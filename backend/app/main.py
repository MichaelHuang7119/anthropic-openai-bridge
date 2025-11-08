"""Main FastAPI application for Anthropic OpenAI Bridge"""
import json
import logging
import asyncio
from typing import Optional, Union
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from openai import RateLimitError, APIError, APIConnectionError
import httpx

from .config import config
from .models import (
    MessagesRequest, CountTokensRequest, CountTokensResponse,
    Message
)
from .model_manager import ModelManager
from .converter import (
    convert_anthropic_request_to_openai,
    convert_openai_response_to_anthropic,
    convert_openai_stream_to_anthropic_async
)
from .client import OpenAIClient
from .utils import openai_response_to_dict
from .api.providers import router as providers_router
from .api.health import router as health_router
from .api.config import router as config_router
from .retry import retry_with_backoff, is_retryable_error

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress verbose httpx/httpcore logging from OpenAI SDK
# This prevents logging every HTTP request, reducing noise in logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

app = FastAPI(
    title="Anthropic OpenAI Bridge",
    description="""
    Anthropic-compatible API proxy service.
    
    ## Claude Code 配置
    
    在 Claude Code 中使用本服务，需要配置以下环境变量：
    
    ```bash
    export ANTHROPIC_BASE_URL=http://localhost:5175
    export ANTHROPIC_API_KEY="any-value"
    ```
    
    然后启动 Claude Code 进行 Vibe Coding。
    
    **注意**：`ANTHROPIC_BASE_URL` 需要替换为实际的前端服务地址。
    """,
    version="1.0.0"
)

model_manager = ModelManager(config)


def count_tokens_estimate(messages: list, model: str) -> int:
    """
    Estimate token count for messages.
    This is a simplified estimation. For accurate counts, you may need
    to use the actual model's tokenizer or call the API.
    """
    # Simple estimation: ~4 characters per token
    total_chars = 0
    for msg in messages:
        if isinstance(msg, dict):
            role = msg.get("role", "")
            content = msg.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            total_chars += len(block.get("text", ""))
                        elif block.get("type") == "image_url":
                            # Images consume tokens based on resolution
                            # Rough estimate: ~85 tokens per image
                            total_chars += 340  # ~85 tokens * 4 chars
            elif isinstance(content, str):
                total_chars += len(content)
        elif isinstance(msg, Message):
            if isinstance(msg.content, str):
                total_chars += len(msg.content)
            elif isinstance(msg.content, list):
                for block in msg.content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            total_chars += len(block.get("text", ""))
                        elif block.get("type") == "image":
                            total_chars += 340
    
    # Add overhead for formatting (role names, etc.)
    overhead = len(messages) * 10
    return int((total_chars / 4) + overhead)


async def count_tokens_using_api(messages: list, provider: OpenAIClient, model: str) -> int:
    """Count tokens by making a dry-run API call if supported."""
    try:
        # Try to get actual token count by making a minimal request
        # Some providers support this, but for now we'll use estimation
        return count_tokens_estimate(messages, model)
    except Exception as e:
        logger.warning(f"Could not get token count from API: {e}, using estimation")
        return count_tokens_estimate(messages, model)


@app.post("/v1/messages")
async def messages(request: Union[MessagesRequest, dict]):
    """Handle Anthropic /v1/messages endpoint."""
    try:
        # Parse request
        if isinstance(request, dict):
            req = MessagesRequest(**request)
        else:
            req = request
        
        # Get provider and model
        provider_config, actual_model = model_manager.get_provider_and_model(req.model)
        client = OpenAIClient(provider_config)
        
        # Convert Anthropic request to OpenAI format
        openai_request = convert_anthropic_request_to_openai(req)
        
        # Filter out potentially unsupported parameters for specific providers
        # Some providers (like modelscope) may not support all OpenAI parameters
        unsupported_params = []
        if provider_config.name == "modelscope":
            # modelscope may not support tool_choice parameter
            if "tool_choice" in openai_request:
                tool_choice_val = openai_request.pop("tool_choice")
                unsupported_params.append(f"tool_choice={tool_choice_val}")
            
            # Normalize messages for modelscope - ensure content is never None or empty
            # Some providers don't handle None content well
            for msg in openai_request.get("messages", []):
                if msg.get("role") == "assistant":
                    # Ensure assistant messages with tool_calls have valid content
                    if "tool_calls" in msg and msg.get("content") is None:
                        msg["content"] = ""  # Set to empty string instead of None
                    elif "tool_calls" in msg and not msg.get("content"):
                        msg["content"] = ""
                elif msg.get("role") == "tool":
                    # Ensure tool messages have non-empty content
                    if not msg.get("content"):
                        msg["content"] = "No result"
            
            # Log if we removed any parameters
            if unsupported_params:
                logger.debug(f"Filtered unsupported parameters for {provider_config.name}: {', '.join(unsupported_params)}")
        
        # Validate and limit max_tokens (per claude-code-proxy pattern)
        # Apply global limits: min(max(request, min_limit), max_limit)
        max_tokens = openai_request.get("max_tokens")
        if max_tokens is not None:
            # Apply global limits (same as claude-code-proxy)
            original_max_tokens = max_tokens
            max_tokens = min(
                max(max_tokens, config.min_tokens_limit),
                config.max_tokens_limit
            )
            openai_request["max_tokens"] = max_tokens
            
            # Log if limit was applied
            if original_max_tokens != max_tokens:
                logger.debug(f"Limited max_tokens from {original_max_tokens} to {max_tokens} (global limits: min={config.min_tokens_limit}, max={config.max_tokens_limit})")
        
        # Make request
        if req.stream:
            # Streaming response
            async def generate():
                try:
                    # Log request details for debugging (only for failed requests)
                    logger.debug(f"Sending request to {provider_config.name} provider: model={actual_model}, max_tokens={openai_request.get('max_tokens')}, has_tools={bool(openai_request.get('tools'))}, message_count={len(openai_request.get('messages', []))}")
                    
                    # Build params, excluding tool_choice if it was filtered
                    api_params = {
                        "model": actual_model,
                        "messages": openai_request["messages"],
                        "stream": True,
                    }
                    if "temperature" in openai_request:
                        api_params["temperature"] = openai_request["temperature"]
                    if "tools" in openai_request:
                        api_params["tools"] = openai_request["tools"]
                    if "max_tokens" in openai_request:
                        api_params["max_tokens"] = openai_request["max_tokens"]
                    # Only pass tool_choice if it exists (wasn't filtered)
                    if "tool_choice" in openai_request:
                        api_params["tool_choice"] = openai_request["tool_choice"]
                    
                    # Calculate input tokens before streaming starts (for real-time display)
                    # This allows clients to see input token count immediately in message_start event
                    messages_list = []
                    for msg in req.messages:
                        if isinstance(msg, Message):
                            messages_list.append({
                                "role": msg.role.value,
                                "content": msg.content
                            })
                        else:
                            messages_list.append(msg)
                    
                    # Estimate input tokens (will be updated with actual value from API if available)
                    initial_input_tokens = count_tokens_estimate(messages_list, actual_model)
                    
                    # Retry logic for streaming requests
                    # Note: For streaming, we can only retry before the stream starts.
                    # Once streaming begins, timeout errors will be handled by the exception handler below.
                    max_retries = provider_config.max_retries
                    retry_count = 0
                    
                    while retry_count <= max_retries:
                        try:
                            # Create request function for retry
                            async def make_stream_request():
                                return await client.chat_completion_async(**api_params)
                            
                            # Use retry mechanism for initial connection
                            # Only retry connection errors, not streaming timeouts
                            openai_stream = await retry_with_backoff(
                                make_stream_request,
                                max_retries=0,  # Don't retry here, handle retries manually for better control
                                provider_name=provider_config.name
                            )
                            
                            # Stream converted chunks with optimized JSON serialization
                            # Using compact separators and pre-allocated strings for better performance
                            # Support event types for better SSE compatibility (per claude-code-proxy pattern)
                            async for chunk in convert_openai_stream_to_anthropic_async(
                                openai_stream, req.model, initial_input_tokens
                            ):
                                # Use faster JSON serialization with compact output
                                # Pre-allocate the SSE format string for better performance
                                json_str = json.dumps(chunk, ensure_ascii=False, separators=(',', ':'))
                                event_type = chunk.get("type", "")
                                # Send with event type for better SSE compatibility (like claude-code-proxy)
                                if event_type:
                                    yield f"event: {event_type}\ndata: {json_str}\n\n"
                                else:
                                    yield f"data: {json_str}\n\n"
                            yield "data: [DONE]\n\n"
                            # Success, break out of retry loop
                            break
                            
                        except (httpx.ReadTimeout, httpx.TimeoutException, httpx.ConnectTimeout, httpx.PoolTimeout, APIConnectionError) as e:
                            retry_count += 1
                            
                            if retry_count <= max_retries:
                                # Calculate delay with exponential backoff
                                delay = min(1.0 * (2.0 ** (retry_count - 1)), 60.0)
                                
                                # Determine error type for better messaging
                                if isinstance(e, (httpx.ConnectTimeout, httpx.PoolTimeout)):
                                    error_type = "connection_timeout"
                                    error_msg = f"Unable to connect to provider '{provider_config.name}'. Connection timeout. Retrying in {delay:.0f}s... (attempt {retry_count}/{max_retries + 1})"
                                elif isinstance(e, (httpx.ReadTimeout, httpx.TimeoutException)):
                                    error_type = "read_timeout"
                                    error_msg = f"Request timeout for provider '{provider_config.name}'. Retrying in {delay:.0f}s... (attempt {retry_count}/{max_retries + 1})"
                                else:
                                    error_type = "connection_error"
                                    error_msg = f"Connection error to provider '{provider_config.name}'. Retrying in {delay:.0f}s... (attempt {retry_count}/{max_retries + 1})"
                                
                                logger.warning(
                                    f"Streaming error for provider '{provider_config.name}' "
                                    f"(attempt {retry_count}/{max_retries + 1}): {type(e).__name__}: {e}. "
                                    f"Retrying in {delay:.2f}s..."
                                )
                                
                                # Send retry notification to client
                                retry_notification = {
                                    "type": "error",
                                    "error": {
                                        "type": error_type,
                                        "message": error_msg,
                                        "provider": provider_config.name,
                                        "retry_count": retry_count,
                                        "max_retries": max_retries + 1,
                                        "retry_delay": delay
                                    }
                                }
                                yield f"data: {json.dumps(retry_notification)}\n\n"
                                
                                await asyncio.sleep(delay)
                                # Continue to retry
                            else:
                                # All retries exhausted
                                logger.error(
                                    f"All retry attempts exhausted for provider '{provider_config.name}'. "
                                    f"Last error: {type(e).__name__}: {e}"
                                )
                                
                                # Send final error to client
                                if isinstance(e, (httpx.ConnectTimeout, httpx.PoolTimeout)):
                                    final_error = {
                                        "type": "error",
                                        "error": {
                                            "type": "connection_timeout",
                                            "message": f"Unable to connect to provider '{provider_config.name}' after {max_retries + 1} attempts. Please check your network connection and provider configuration.",
                                            "provider": provider_config.name
                                        }
                                    }
                                elif isinstance(e, (httpx.ReadTimeout, httpx.TimeoutException)):
                                    final_error = {
                                        "type": "error",
                                        "error": {
                                            "type": "timeout_error",
                                            "message": f"Request timeout for provider '{provider_config.name}' after {max_retries + 1} attempts. The request took too long to respond.",
                                            "provider": provider_config.name
                                        }
                                    }
                                else:
                                    final_error = {
                                        "type": "error",
                                        "error": {
                                            "type": "connection_error",
                                            "message": f"Connection error to provider '{provider_config.name}' after {max_retries + 1} attempts: {str(e)}",
                                            "provider": provider_config.name
                                        }
                                    }
                                yield f"data: {json.dumps(final_error)}\n\n"
                                raise
                        except Exception as e:
                            # For other exceptions, check if retryable
                            if is_retryable_error(e) and retry_count < max_retries:
                                retry_count += 1
                                delay = min(1.0 * (2.0 ** (retry_count - 1)), 60.0)
                                logger.warning(
                                    f"Retryable error for provider '{provider_config.name}' "
                                    f"(attempt {retry_count}/{max_retries + 1}): {type(e).__name__}. "
                                    f"Retrying in {delay:.2f}s..."
                                )
                                await asyncio.sleep(delay)
                                continue
                            else:
                                # Not retryable or retries exhausted, re-raise
                                raise
                except RateLimitError as e:
                    logger.warning(f"Rate limit error from provider {provider_config.name}: {e}")
                    error_response = {
                        "type": "error",
                        "error": {
                            "type": "rate_limit_error",
                            "message": f"Rate limit exceeded for provider '{provider_config.name}'. Please try again later.",
                            "provider": provider_config.name
                        }
                    }
                    yield f"data: {json.dumps(error_response)}\n\n"
                except (httpx.ConnectTimeout, httpx.PoolTimeout) as e:
                    logger.error(f"Connection timeout from provider {provider_config.name}: {e}")
                    error_response = {
                        "type": "error",
                        "error": {
                            "type": "connection_timeout",
                            "message": f"Unable to connect to provider '{provider_config.name}'. Connection timeout. Please check your network connection and provider configuration.",
                            "provider": provider_config.name
                        }
                    }
                    yield f"data: {json.dumps(error_response)}\n\n"
                except APIConnectionError as e:
                    logger.error(f"Connection error from provider {provider_config.name}: {e}")
                    error_response = {
                        "type": "error",
                        "error": {
                            "type": "connection_error",
                            "message": f"Connection error to provider '{provider_config.name}': {str(e)}",
                            "provider": provider_config.name
                        }
                    }
                    yield f"data: {json.dumps(error_response)}\n\n"
                except (httpx.ReadTimeout, httpx.TimeoutException) as e:
                    logger.error(f"Timeout error from provider {provider_config.name}: {e}")
                    error_response = {
                        "type": "error",
                        "error": {
                            "type": "timeout_error",
                            "message": f"Request timeout for provider '{provider_config.name}'. The request took too long to respond. Please try again or increase the timeout setting.",
                            "provider": provider_config.name
                        }
                    }
                    yield f"data: {json.dumps(error_response)}\n\n"
                except APIError as e:
                    # Log detailed error information for debugging
                    error_detail = str(e)
                    logger.error(f"API error from provider {provider_config.name}: {e}")
                    # Log request details when error occurs (for debugging format issues)
                    if provider_config.name == "modelscope":
                        logger.error(f"Request details for modelscope: model={actual_model}, "
                                   f"max_tokens={api_params.get('max_tokens')}, "
                                   f"has_tools={bool(api_params.get('tools'))}, "
                                   f"tool_count={len(api_params.get('tools', []))}, "
                                   f"message_count={len(api_params.get('messages', []))}, "
                                   f"has_tool_choice={'tool_choice' in api_params}")
                        # Log detailed message structure for all messages
                        import json as json_module
                        for idx, msg in enumerate(api_params.get("messages", [])):
                            msg_info = {
                                "index": idx,
                                "role": msg.get("role"),
                                "has_content": "content" in msg,
                                "content_type": type(msg.get("content")).__name__ if "content" in msg else "missing",
                                "has_tool_calls": "tool_calls" in msg,
                                "has_tool_call_id": "tool_call_id" in msg,
                            }
                            # Log content preview (truncated)
                            if "content" in msg:
                                content = msg.get("content")
                                if isinstance(content, str):
                                    msg_info["content_preview"] = content[:100] if len(content) > 100 else content
                                elif isinstance(content, list):
                                    msg_info["content_preview"] = f"list[{len(content)} items]"
                                else:
                                    msg_info["content_preview"] = str(content)[:100]
                            logger.error(f"Message {idx} structure: {json_module.dumps(msg_info, ensure_ascii=False)}")
                    
                    error_response = {
                        "type": "error",
                        "error": {
                            "type": "api_error",
                            "message": f"API error from provider '{provider_config.name}': {error_detail}",
                            "provider": provider_config.name
                        }
                    }
                    yield f"data: {json.dumps(error_response)}\n\n"
                except Exception as e:
                    logger.error(f"Unexpected error in streaming response: {e}", exc_info=True)
                    error_response = {
                        "type": "error",
                        "error": {
                            "type": "internal_error",
                            "message": f"Internal error: {str(e)}"
                        }
                    }
                    yield f"data: {json.dumps(error_response)}\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive"
                }
            )
        else:
            # Non-streaming response
            try:
                # Log request details for debugging
                logger.debug(f"Sending request to {provider_config.name} provider: model={actual_model}, max_tokens={openai_request.get('max_tokens')}, has_tools={bool(openai_request.get('tools'))}, message_count={len(openai_request.get('messages', []))}")
                
                # Build params, excluding tool_choice if it was filtered
                api_params = {
                    "model": actual_model,
                    "messages": openai_request["messages"],
                    "stream": False,
                }
                if "temperature" in openai_request:
                    api_params["temperature"] = openai_request["temperature"]
                if "tools" in openai_request:
                    api_params["tools"] = openai_request["tools"]
                if "max_tokens" in openai_request:
                    api_params["max_tokens"] = openai_request["max_tokens"]
                # Only pass tool_choice if it exists (wasn't filtered)
                if "tool_choice" in openai_request:
                    api_params["tool_choice"] = openai_request["tool_choice"]
                
                # Retry logic for non-streaming requests
                async def make_request():
                    # For sync client, we need to wrap it differently
                    # Since chat_completion is sync, we'll use asyncio.to_thread
                    return await asyncio.to_thread(client.chat_completion, **api_params)
                
                openai_response = await retry_with_backoff(
                    make_request,
                    max_retries=provider_config.max_retries,
                    initial_delay=1.0,
                    max_delay=60.0,
                    exponential_base=2.0,
                    retryable_exceptions=(httpx.ReadTimeout, httpx.TimeoutException, httpx.ConnectTimeout, httpx.PoolTimeout, APIConnectionError),
                    provider_name=provider_config.name
                )
            except RateLimitError as e:
                logger.warning(f"Rate limit error from provider {provider_config.name}: {e}")
                raise HTTPException(
                    status_code=429,
                    detail={
                        "type": "rate_limit_error",
                        "message": f"Rate limit exceeded for provider '{provider_config.name}'. Please try again later.",
                        "provider": provider_config.name
                    }
                )
            except (httpx.ConnectTimeout, httpx.PoolTimeout) as e:
                logger.error(f"Connection timeout from provider {provider_config.name}: {e}")
                raise HTTPException(
                    status_code=503,
                    detail={
                        "type": "connection_timeout",
                        "message": f"Unable to connect to provider '{provider_config.name}'. Connection timeout. Please check your network connection and provider configuration.",
                        "provider": provider_config.name
                    }
                )
            except APIConnectionError as e:
                logger.error(f"Connection error from provider {provider_config.name}: {e}")
                raise HTTPException(
                    status_code=503,
                    detail={
                        "type": "connection_error",
                        "message": f"Connection error to provider '{provider_config.name}': {str(e)}",
                        "provider": provider_config.name
                    }
                )
            except (httpx.ReadTimeout, httpx.TimeoutException) as e:
                logger.error(f"Timeout error from provider {provider_config.name}: {e}")
                raise HTTPException(
                    status_code=504,
                    detail={
                        "type": "timeout_error",
                        "message": f"Request timeout for provider '{provider_config.name}'. The request took too long to respond. Please try again or increase the timeout setting.",
                        "provider": provider_config.name
                    }
                )
            except APIError as e:
                # Log detailed error information for debugging
                error_detail = str(e)
                logger.error(f"API error from provider {provider_config.name}: {e}")
                # Log request details when error occurs (for debugging format issues)
                if provider_config.name == "modelscope":
                    logger.error(f"Request details for modelscope: model={actual_model}, "
                               f"max_tokens={api_params.get('max_tokens')}, "
                               f"has_tools={bool(api_params.get('tools'))}, "
                               f"tool_count={len(api_params.get('tools', []))}, "
                               f"message_count={len(api_params.get('messages', []))}, "
                               f"has_tool_choice={'tool_choice' in api_params}")
                    # Log detailed message structure for all messages
                    import json as json_module
                    for idx, msg in enumerate(api_params.get("messages", [])):
                        msg_info = {
                            "index": idx,
                            "role": msg.get("role"),
                            "has_content": "content" in msg,
                            "content_type": type(msg.get("content")).__name__ if "content" in msg else "missing",
                            "has_tool_calls": "tool_calls" in msg,
                            "has_tool_call_id": "tool_call_id" in msg,
                        }
                        # Log content preview (truncated)
                        if "content" in msg:
                            content = msg.get("content")
                            if isinstance(content, str):
                                msg_info["content_preview"] = content[:100] if len(content) > 100 else content
                            elif isinstance(content, list):
                                msg_info["content_preview"] = f"list[{len(content)} items]"
                            else:
                                msg_info["content_preview"] = str(content)[:100]
                        logger.error(f"Message {idx} structure: {json_module.dumps(msg_info, ensure_ascii=False)}")
                
                raise HTTPException(
                    status_code=502,
                    detail={
                        "type": "api_error",
                        "message": f"API error from provider '{provider_config.name}': {error_detail}",
                        "provider": provider_config.name
                    }
                )
            
            # Convert response
            openai_dict = openai_response_to_dict(openai_response)
            
            anthropic_response = convert_openai_response_to_anthropic(
                openai_dict,
                req.model,
                stream=False
            )
            
            return anthropic_response
    
    except HTTPException:
        # Re-raise HTTP exceptions (RateLimitError, APIError, etc.)
        raise
    except ValueError as e:
        logger.error(f"Value error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/v1/messages/count_tokens")
async def count_tokens(request: Union[CountTokensRequest, dict]):
    """Handle Anthropic /v1/messages/count_tokens endpoint."""
    try:
        # Parse request
        if isinstance(request, dict):
            req = CountTokensRequest(**request)
        else:
            req = request
        
        # Get provider and model
        provider_config, actual_model = model_manager.get_provider_and_model(req.model)
        client = OpenAIClient(provider_config)
        
        # Convert messages to list of dicts for counting
        messages_list = []
        for msg in req.messages:
            if isinstance(msg, Message):
                messages_list.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
            else:
                messages_list.append(msg)
        
        # Count tokens
        try:
            # Try to get accurate count from API if possible
            token_count = await count_tokens_using_api(
                messages_list, client, actual_model
            )
        except Exception as e:
            logger.warning(f"Using estimation for token count: {e}")
            token_count = count_tokens_estimate(messages_list, actual_model)
        
        return CountTokensResponse(
            model=req.model,
            input_tokens=token_count
        )
    
    except ValueError as e:
        logger.error(f"Value error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error counting tokens: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Anthropic OpenAI Bridge",
        "version": "1.0.0",
        "description": "Anthropic-compatible API proxy service",
        "claude_code_config": {
            "instructions": "在 Claude Code 中配置以下环境变量：",
            "environment_variables": {
                "ANTHROPIC_BASE_URL": "http://localhost:5175",
                "ANTHROPIC_API_KEY": "any-value"
            },
            "note": "ANTHROPIC_BASE_URL 需要替换为实际的前端服务地址"
        },
        "endpoints": [
            "/v1/messages",
            "/v1/messages/count_tokens",
            "/health",
            "/api/providers",
            "/api/health",
            "/api/config"
        ]
    }

# Register API routers
app.include_router(providers_router)
app.include_router(health_router)
app.include_router(config_router)

