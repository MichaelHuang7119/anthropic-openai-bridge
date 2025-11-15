"""Message handling service for processing Anthropic API requests."""
import json
import logging
import asyncio
import time
import uuid
from typing import Optional, Union, List, Dict, Any
from datetime import datetime
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from openai import RateLimitError, APIError, APIConnectionError
import httpx

from ..config import config
from ..core import MessagesRequest, Message, ModelManager
from ..converters import (
    convert_anthropic_request_to_openai,
    convert_openai_response_to_anthropic,
    convert_openai_stream_to_anthropic_async
)
from ..infrastructure import OpenAIClient, retry_with_backoff, is_retryable_error, CacheKey, get_cache_manager
from ..utils import openai_response_to_dict
from ..database import get_database
from .token_counter import count_tokens_estimate

logger = logging.getLogger(__name__)


class MessageService:
    """Service for handling message requests."""
    
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
    
    async def handle_messages(
        self,
        request: Union[MessagesRequest, dict],
        api_user: dict,
        exclude_providers: Optional[List[str]] = None,
        exclude_models: Optional[Dict[str, List[str]]] = None
    ):
        """Internal function to handle messages request with optional exclude parameters.
        
        Rotates through all models in a category within the same provider before switching providers.
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        input_tokens = None
        output_tokens = None
        status_code = 200
        error_message = None

        try:
            # Parse request
            if isinstance(request, dict):
                req = MessagesRequest(**request)
            else:
                req = request

            # Initialize exclude parameters
            current_exclude_providers = exclude_providers or []
            current_exclude_models = exclude_models.copy() if exclude_models else {}
            
            # Track which models we've tried for the current provider
            current_provider_name = None
            failed_models_for_current_provider = []
            
            # Model rotation loop: try models in the same provider/category until one succeeds
            max_model_attempts = 10  # Prevent infinite loops
            model_attempt_count = 0
            
            while model_attempt_count < max_model_attempts:
                model_attempt_count += 1
                
                try:
                    # Get provider and model with current exclude parameters
                    # If provider is specified in request, use it as preferred_provider
                    try:
                        provider_config, actual_model = self.model_manager.get_provider_and_model(
                            req.model,
                            exclude_providers=current_exclude_providers,
                            exclude_models=current_exclude_models,
                            preferred_provider=getattr(req, 'provider', None)
                        )
                    except ValueError as ve:
                        # No provider/model found - this means all providers/models in this category are exhausted
                        # Log and break out of the loop
                        logger.warning(f"No available provider/model found: {ve}")
                        # If we've tried at least one provider, exclude the current provider and try again
                        if current_provider_name and current_provider_name not in current_exclude_providers:
                            logger.debug(f"Excluding provider {current_provider_name} as all its models are exhausted")
                            current_exclude_providers.append(current_provider_name)
                            current_provider_name = None
                            failed_models_for_current_provider = []
                            # Continue to try next provider
                            continue
                        else:
                            # All providers exhausted, break out
                            break
                    
                    # Track current provider for model rotation
                    if current_provider_name is None:
                        current_provider_name = provider_config.name
                        failed_models_for_current_provider = []
                    elif current_provider_name != provider_config.name:
                        # Provider changed, reset failed models list
                        current_provider_name = provider_config.name
                        failed_models_for_current_provider = []
                    
                    # Check if we've already tried this model
                    if actual_model in failed_models_for_current_provider:
                        # All models in this provider's category have been tried, switch to next provider
                        if current_provider_name not in current_exclude_providers:
                            current_exclude_providers.append(current_provider_name)
                        current_provider_name = None
                        failed_models_for_current_provider = []
                        continue
                    
                    client = OpenAIClient(provider_config)

                    # Try to get from cache for non-streaming requests
                    cache_enabled = config.app_config.cache.enabled and not req.stream
                    cached_response = None
                    cache_key = None

                    if cache_enabled:
                        # Generate cache key first
                        # We need the openai_request for this, so convert first
                        openai_request_for_cache = convert_anthropic_request_to_openai(req)

                        cache_key = CacheKey.generate_key(
                            model=actual_model,
                            messages=openai_request_for_cache.get("messages", []),
                            max_tokens=openai_request_for_cache.get("max_tokens"),
                            temperature=openai_request_for_cache.get("temperature"),
                            tools=openai_request_for_cache.get("tools"),
                            stream=req.stream,
                            provider=provider_config.name
                        )

                        # Try to get from cache
                        cache_manager = get_cache_manager()
                        cached_response = await cache_manager.get(cache_key)

                        if cached_response is not None:
                            logger.info(f"Cache hit for provider {provider_config.name}, model {actual_model}")
                            # Log to database (successful cache hit)
                            db = get_database()
                            await db.log_request(
                                request_id=request_id,
                                provider_name=provider_config.name,
                                model=actual_model,
                                request_params={
                                    "model": req.model,
                                    "stream": req.stream,
                                    "cache_hit": True
                                },
                                status_code=200,
                                response_time_ms=(time.time() - start_time) * 1000
                            )
                            return cached_response

                    # Convert Anthropic request to OpenAI format
                    openai_request = convert_anthropic_request_to_openai(req)
                    
                    # Filter and validate request
                    self._filter_unsupported_params(provider_config, openai_request)
                    self._validate_max_tokens(openai_request)
                    
                    # Make request
                    if req.stream:
                        return await self._handle_streaming_request(
                            req, provider_config, actual_model, client,
                            openai_request, request_id, start_time
                        )
                    else:
                        return await self._handle_non_streaming_request(
                            req, provider_config, actual_model, client,
                            openai_request, cache_enabled, cache_key,
                            cached_response, request_id, start_time
                        )
                        
                except (RateLimitError, httpx.ConnectTimeout, httpx.PoolTimeout, 
                        APIConnectionError, httpx.ReadTimeout, httpx.TimeoutException, 
                        APIError, HTTPException) as model_error:
                    # Model failed, add to exclude list and try next model
                    logger.warning(
                        f"Model '{actual_model}' from provider '{provider_config.name}' failed: {type(model_error).__name__}: {model_error}. "
                        f"Trying next model in category..."
                    )
                    
                    # Add failed model to exclude list
                    if current_provider_name not in current_exclude_models:
                        current_exclude_models[current_provider_name] = []
                    if actual_model not in current_exclude_models[current_provider_name]:
                        current_exclude_models[current_provider_name].append(actual_model)
                        failed_models_for_current_provider.append(actual_model)
                    
                    # Continue to next iteration to try next model
                    continue
                    
                except Exception as model_error:
                    # Unexpected error, log and try next model
                    logger.error(
                        f"Unexpected error with model '{actual_model}' from provider '{provider_config.name}': {type(model_error).__name__}: {model_error}. "
                        f"Trying next model in category...",
                        exc_info=True
                    )
                    
                    # Add failed model to exclude list
                    if current_provider_name not in current_exclude_models:
                        current_exclude_models[current_provider_name] = []
                    if actual_model not in current_exclude_models[current_provider_name]:
                        current_exclude_models[current_provider_name].append(actual_model)
                        failed_models_for_current_provider.append(actual_model)
                    
                    # Continue to next iteration to try next model
                    continue
            
            # If we reach here, all model attempts failed
            # Re-raise the last exception or raise a generic error
            raise ValueError(
                f"All models exhausted for Anthropic model '{req.model}'. "
                f"No available models found after {model_attempt_count} attempts."
            )
        
        except HTTPException as e:
            # Log error to database
            error_message = str(e.detail)
            status_code = e.status_code
            db = get_database()
            await db.log_request(
                request_id=request_id,
                provider_name=provider_config.name if 'provider_config' in locals() else "unknown",
                model=actual_model if 'actual_model' in locals() else req.model,
                request_params=openai_request if 'openai_request' in locals() else {},
                status_code=status_code,
                error_message=error_message,
                response_time_ms=(time.time() - start_time) * 1000
            )
            # Re-raise HTTP exceptions (RateLimitError, APIError, etc.)
            raise
        except ValueError as e:
            logger.error(f"Value error: {e}")
            # Log error to database
            error_message = str(e)
            status_code = 400
            db = get_database()
            if 'provider_config' in locals():
                await db.log_request(
                    request_id=request_id,
                    provider_name=provider_config.name,
                    model=actual_model if 'actual_model' in locals() else req.model,
                    request_params=openai_request if 'openai_request' in locals() else {},
                    status_code=status_code,
                    error_message=error_message,
                    response_time_ms=(time.time() - start_time) * 1000
                )
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            # Log error to database
            error_message = str(e)
            status_code = 500
            db = get_database()
            if 'provider_config' in locals():
                await db.log_request(
                    request_id=request_id,
                    provider_name=provider_config.name,
                    model=actual_model if 'actual_model' in locals() else req.model,
                    request_params=openai_request if 'openai_request' in locals() else {},
                    status_code=status_code,
                    error_message=error_message,
                    response_time_ms=(time.time() - start_time) * 1000
                )
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    def _filter_unsupported_params(self, provider_config, openai_request: dict):
        """Filter out potentially unsupported parameters for specific providers."""
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
    
    def _validate_max_tokens(self, openai_request: dict):
        """Validate and limit max_tokens (per claude-code-proxy pattern)."""
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
    
    async def _handle_streaming_request(
        self, req: MessagesRequest, provider_config, actual_model: str,
        client: OpenAIClient, openai_request: dict, request_id: str, start_time: float
    ) -> StreamingResponse:
        """Handle streaming request."""
        async def generate():
            try:
                # Log request details for debugging
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
                
                # Calculate input tokens before streaming starts
                messages_list = []
                for msg in req.messages:
                    if isinstance(msg, Message):
                        messages_list.append({
                            "role": msg.role.value,
                            "content": msg.content
                        })
                    else:
                        messages_list.append(msg)
                
                # Estimate input tokens
                initial_input_tokens = count_tokens_estimate(messages_list, actual_model)
                
                # Retry logic for streaming requests
                max_retries = provider_config.max_retries
                retry_count = 0
                
                while retry_count <= max_retries:
                    try:
                        # Create request function for retry
                        async def make_stream_request():
                            return await client.chat_completion_async(**api_params)
                        
                        # Use retry mechanism for initial connection
                        openai_stream = await retry_with_backoff(
                            make_stream_request,
                            max_retries=0,  # Don't retry here, handle retries manually for better control
                            provider_name=provider_config.name
                        )
                        
                        # Stream converted chunks
                        async for chunk in convert_openai_stream_to_anthropic_async(
                            openai_stream, req.model, initial_input_tokens
                        ):
                            json_str = json.dumps(chunk, ensure_ascii=False, separators=(',', ':'))
                            event_type = chunk.get("type", "")
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
                error_detail = str(e)
                logger.error(f"API error from provider {provider_config.name}: {e}")
                # Log request details when error occurs (for debugging format issues)
                if provider_config.name == "modelscope":
                    self._log_modelscope_error(api_params, actual_model)
                
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
    
    async def _handle_non_streaming_request(
        self, req: MessagesRequest, provider_config, actual_model: str,
        client: OpenAIClient, openai_request: dict, cache_enabled: bool,
        cache_key: Optional[str], cached_response: Optional[Any],
        request_id: str, start_time: float
    ) -> dict:
        """Handle non-streaming request."""
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
            error_detail = str(e)
            logger.error(f"API error from provider {provider_config.name}: {e}")
            # Log request details when error occurs (for debugging format issues)
            if provider_config.name == "modelscope":
                self._log_modelscope_error(api_params, actual_model)
            
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

        # Cache the response if caching is enabled
        if cache_enabled and cached_response is None:
            try:
                cache_manager = get_cache_manager()
                await cache_manager.set(
                    cache_key,
                    anthropic_response,
                    ttl=config.app_config.cache.default_ttl
                )
                logger.info(f"Cached response for provider {provider_config.name}, model {actual_model}")
            except Exception as e:
                # Don't fail the request if caching fails
                logger.warning(f"Failed to cache response: {e}")

        # Extract token usage from response if available
        usage = anthropic_response.get("usage", {})
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")

        # Log to database (successful request)
        db = get_database()
        await db.log_request(
            request_id=request_id,
            provider_name=provider_config.name,
            model=actual_model,
            request_params=openai_request,
            response_data=anthropic_response,
            status_code=200,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            response_time_ms=(time.time() - start_time) * 1000
        )

        # Update token usage statistics
        if input_tokens or output_tokens:
            today = datetime.now().strftime("%Y-%m-%d")
            # Estimated cost: $0.01 per 1K input tokens, $0.03 per 1K output tokens
            cost_estimate = (
                (input_tokens or 0) * 0.00001 +
                (output_tokens or 0) * 0.00003
            )
            await db.update_token_usage(
                date=today,
                provider_name=provider_config.name,
                model=actual_model,
                input_tokens=input_tokens or 0,
                output_tokens=output_tokens or 0,
                cost_estimate=cost_estimate
            )

        return anthropic_response
    
    def _log_modelscope_error(self, api_params: dict, actual_model: str):
        """Log detailed error information for modelscope provider."""
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

