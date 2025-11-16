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
from ..infrastructure import OpenAIClient, AnthropicClient, retry_with_backoff, is_retryable_error, CacheKey, get_cache_manager
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
                    
                    # Check provider API format
                    api_format = getattr(provider_config, 'api_format', 'openai').lower()
                    
                    if api_format == 'anthropic':
                        # Direct forwarding for Anthropic format providers
                        return await self._handle_anthropic_direct_request(
                            req, provider_config, actual_model, request_id, start_time
                        )
                    else:
                        # OpenAI format - use conversion logic (default behavior)
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
                        APIError, httpx.HTTPStatusError) as model_error:
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
                    
                except HTTPException as http_error:
                    # HTTPException from conversion or validation - treat as model failure
                    # Only retry if it's a 5xx error (server error), not 4xx (client error)
                    if http_error.status_code >= 500:
                        logger.warning(
                            f"Model '{actual_model}' from provider '{provider_config.name}' failed with HTTP {http_error.status_code}: {http_error.detail}. "
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
                    else:
                        # 4xx errors (like 429 rate limit) should be re-raised
                        raise
                    
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

            # Estimate input tokens for failed requests
            failed_request_input_tokens = 0
            if 'openai_request' in locals() and openai_request and 'messages' in openai_request:
                try:
                    failed_request_input_tokens = count_tokens_estimate(
                        openai_request.get('messages', []),
                        actual_model if 'actual_model' in locals() else req.model
                    )
                except:
                    pass

            await db.log_request(
                request_id=request_id,
                provider_name=provider_config.name if 'provider_config' in locals() else "unknown",
                model=actual_model if 'actual_model' in locals() else req.model,
                request_params=openai_request if 'openai_request' in locals() else {},
                status_code=status_code,
                error_message=error_message,
                input_tokens=failed_request_input_tokens,
                response_time_ms=(time.time() - start_time) * 1000
            )

            # Also update token_usage table for failed requests
            # This ensures consistency between provider_stats and token_usage
            if failed_request_input_tokens > 0:
                today = datetime.now().strftime("%Y-%m-%d")
                cost_estimate = failed_request_input_tokens * 0.00001  # Estimate only input tokens
                await db.update_token_usage(
                    date=today,
                    provider_name=provider_config.name if 'provider_config' in locals() else "unknown",
                    model=actual_model if 'actual_model' in locals() else req.model,
                    input_tokens=failed_request_input_tokens,
                    output_tokens=0,
                    cost_estimate=cost_estimate
                )

            # Re-raise HTTP exceptions (RateLimitError, APIError, etc.)
            raise
        except ValueError as e:
            logger.error(f"Value error: {e}")
            # Log error to database
            error_message = str(e)
            status_code = 400
            db = get_database()

            # Estimate input tokens for failed requests
            failed_request_input_tokens = 0
            if 'openai_request' in locals() and openai_request and 'messages' in openai_request:
                try:
                    failed_request_input_tokens = count_tokens_estimate(
                        openai_request.get('messages', []),
                        actual_model if 'actual_model' in locals() else req.model
                    )
                except:
                    pass

            if 'provider_config' in locals():
                await db.log_request(
                    request_id=request_id,
                    provider_name=provider_config.name,
                    model=actual_model if 'actual_model' in locals() else req.model,
                    request_params=openai_request if 'openai_request' in locals() else {},
                    status_code=status_code,
                    error_message=error_message,
                    input_tokens=failed_request_input_tokens,
                    response_time_ms=(time.time() - start_time) * 1000
                )

                # Also update token_usage table for failed requests
                if failed_request_input_tokens > 0:
                    today = datetime.now().strftime("%Y-%m-%d")
                    cost_estimate = failed_request_input_tokens * 0.00001
                    await db.update_token_usage(
                        date=today,
                        provider_name=provider_config.name,
                        model=actual_model if 'actual_model' in locals() else req.model,
                        input_tokens=failed_request_input_tokens,
                        output_tokens=0,
                        cost_estimate=cost_estimate
                    )

            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            # Log error to database
            error_message = str(e)
            status_code = 500
            db = get_database()

            # Estimate input tokens for failed requests
            failed_request_input_tokens = 0
            if 'openai_request' in locals() and openai_request and 'messages' in openai_request:
                try:
                    failed_request_input_tokens = count_tokens_estimate(
                        openai_request.get('messages', []),
                        actual_model if 'actual_model' in locals() else req.model
                    )
                except:
                    pass

            if 'provider_config' in locals():
                await db.log_request(
                    request_id=request_id,
                    provider_name=provider_config.name,
                    model=actual_model if 'actual_model' in locals() else req.model,
                    request_params=openai_request if 'openai_request' in locals() else {},
                    status_code=status_code,
                    error_message=error_message,
                    input_tokens=failed_request_input_tokens,
                    response_time_ms=(time.time() - start_time) * 1000
                )

                # Also update token_usage table for failed requests
                if failed_request_input_tokens > 0:
                    today = datetime.now().strftime("%Y-%m-%d")
                    cost_estimate = failed_request_input_tokens * 0.00001
                    await db.update_token_usage(
                        date=today,
                        provider_name=provider_config.name,
                        model=actual_model if 'actual_model' in locals() else req.model,
                        input_tokens=failed_request_input_tokens,
                        output_tokens=0,
                        cost_estimate=cost_estimate
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
            
            # modelscope requires enable_thinking to be false for non-streaming calls
            # Remove it if present (or set to false if needed)
            if "enable_thinking" in openai_request:
                enable_thinking = openai_request.pop("enable_thinking")
                if enable_thinking:
                    unsupported_params.append(f"enable_thinking={enable_thinking} (removed, must be false for non-streaming)")
            
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
                        chunk_count = 0
                        async for chunk in convert_openai_stream_to_anthropic_async(
                            openai_stream, req.model, initial_input_tokens
                        ):
                            chunk_count += 1
                            json_str = json.dumps(chunk, ensure_ascii=False, separators=(',', ':'))
                            event_type = chunk.get("type", "")
                            if event_type:
                                yield f"event: {event_type}\ndata: {json_str}\n\n"
                            else:
                                yield f"data: {json_str}\n\n"
                        
                        # Check if we received any chunks - if not, this might indicate a problem
                        if chunk_count == 0:
                            logger.warning(
                                f"Streaming request to {provider_config.name} (OpenAI format) completed without any chunks. "
                                f"Model: {actual_model}, Request ID: {request_id}"
                            )
                            # Even if no chunks were received, we should still send [DONE]
                            # to properly close the stream, but log it for debugging
                        
                        yield f"data: [DONE]\n\n"
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
                            yield f"event: error\ndata: {json.dumps(retry_notification)}\n\n"
                            
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
                            yield f"event: error\ndata: {json.dumps(final_error)}\n\n"
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
                yield f"event: error\ndata: {json.dumps(error_response)}\n\n"
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
                yield f"event: error\ndata: {json.dumps(error_response)}\n\n"
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
                yield f"event: error\ndata: {json.dumps(error_response)}\n\n"
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
                yield f"event: error\ndata: {json.dumps(error_response)}\n\n"
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
                yield f"event: error\ndata: {json.dumps(error_response)}\n\n"
            except Exception as e:
                logger.error(f"Unexpected error in streaming response: {e}", exc_info=True)
                error_response = {
                    "type": "error",
                    "error": {
                        "type": "internal_error",
                        "message": f"Internal error: {str(e)}"
                    }
                }
                yield f"event: error\ndata: {json.dumps(error_response)}\n\n"
        
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
            
            # Build params, excluding tool_choice and enable_thinking if they were filtered
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
            # Explicitly exclude enable_thinking for non-streaming calls (modelscope requirement)
            # modelscope API requires enable_thinking to be false (or absent) for non-streaming calls
            if "enable_thinking" in openai_request:
                enable_thinking_val = openai_request.get("enable_thinking")
                if enable_thinking_val:
                    logger.debug(f"Removing enable_thinking={enable_thinking_val} for non-streaming call to {provider_config.name}")
                # Don't include enable_thinking in api_params for non-streaming
            # Also check if it somehow got into api_params and remove it
            if "enable_thinking" in api_params:
                del api_params["enable_thinking"]
            
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
        except Exception as e:
            # Catch any other unexpected exceptions during API call
            logger.error(f"Unexpected error during API call to {provider_config.name}: {type(e).__name__}: {e}", exc_info=True)
            raise HTTPException(
                status_code=502,
                detail={
                    "type": "api_error",
                    "message": f"Unexpected error from provider '{provider_config.name}': {str(e)}",
                    "provider": provider_config.name
                }
            )
        
        # Convert response
        try:
            openai_dict = openai_response_to_dict(openai_response)
        except Exception as e:
            logger.error(f"Failed to convert response from {provider_config.name}: {type(e).__name__}: {e}", exc_info=True)
            raise HTTPException(
                status_code=502,
                detail={
                    "type": "api_error",
                    "message": f"Failed to process response from provider '{provider_config.name}': {str(e)}",
                    "provider": provider_config.name
                }
            )
        
        # Validate response before conversion
        # Check if response is a dict
        if not isinstance(openai_dict, dict):
            logger.error(f"Invalid response type from {provider_config.name}: {type(openai_dict)}. Expected dict.")
            raise HTTPException(
                status_code=502,
                detail={
                    "type": "api_error",
                    "message": f"Invalid response format from provider '{provider_config.name}': expected dict, got {type(openai_dict).__name__}",
                    "provider": provider_config.name
                }
            )
        
        choices = openai_dict.get('choices')
        
        # Handle cases where choices is None, empty list, or missing
        if choices is None or (isinstance(choices, list) and len(choices) == 0):
            # Check for explicit error in response
            error_info = openai_dict.get('error', {})
            if error_info:
                error_msg = error_info.get('message', 'Unknown API error')
                error_type = error_info.get('type', 'api_error')
                logger.error(f"API returned error response from {provider_config.name}: {error_type}: {error_msg}")
                raise HTTPException(
                    status_code=502,
                    detail={
                        "type": "api_error",
                        "message": f"API error from provider '{provider_config.name}': {error_msg}",
                        "provider": provider_config.name
                    }
                )
            
            # Check usage - if all tokens are 0, this might indicate a failed request
            usage = openai_dict.get('usage', {})
            total_tokens = usage.get('total_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            
            # If choices is None (not empty list), this is likely an error response
            if choices is None:
                logger.error(
                    f"Invalid response from {provider_config.name}: choices is None. "
                    f"This usually indicates the API request failed or was rejected. "
                    f"Response: {openai_dict}"
                )
                raise HTTPException(
                    status_code=502,
                    detail={
                        "type": "api_error",
                        "message": f"Provider '{provider_config.name}' returned an invalid response: no choices generated. "
                                   f"This may indicate the request was rejected or the model failed to process it.",
                        "provider": provider_config.name,
                        "model": actual_model
                    }
                )
            else:
                # Empty list - also invalid but different from None
                logger.error(
                    f"Invalid response from {provider_config.name}: choices is empty list. "
                    f"Response: {openai_dict}"
                )
                raise HTTPException(
                    status_code=502,
                    detail={
                        "type": "api_error",
                        "message": f"Provider '{provider_config.name}' returned an empty response: no choices in response",
                        "provider": provider_config.name,
                        "model": actual_model
                    }
                )

        try:
            anthropic_response = convert_openai_response_to_anthropic(
                openai_dict,
                req.model,
                stream=False
            )
        except ValueError as e:
            # Handle conversion errors (e.g., invalid response format)
            logger.error(f"Failed to convert response from {provider_config.name}: {e}")
            raise HTTPException(
                status_code=502,
                detail={
                    "type": "api_error",
                    "message": f"Failed to process response from provider '{provider_config.name}': {str(e)}",
                    "provider": provider_config.name
                }
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
    
    async def _handle_anthropic_direct_request(
        self,
        req: MessagesRequest,
        provider_config,
        actual_model: str,
        request_id: str,
        start_time: float
    ):
        """Handle direct Anthropic format request (no conversion needed)."""
        client = AnthropicClient(provider_config)
        
        try:
            # Convert MessagesRequest to dict for direct forwarding
            if isinstance(req, dict):
                anthropic_request = req.copy()
            else:
                # Use model_dump to convert Pydantic model to dict
                anthropic_request = req.model_dump(exclude_none=True, exclude_unset=True)
            
            # Normalize messages content format: ensure content is always an array
            # Some APIs (like aiping) require content to be in array format [{"type": "text", "text": "..."}]
            if "messages" in anthropic_request:
                normalized_messages = []
                for msg in anthropic_request["messages"]:
                    normalized_msg = msg.copy() if isinstance(msg, dict) else dict(msg)
                    content = normalized_msg.get("content")
                    
                    # Convert string content to array format
                    if isinstance(content, str):
                        normalized_msg["content"] = [{"type": "text", "text": content}]
                    # Ensure array content has proper structure
                    elif isinstance(content, list):
                        normalized_content = []
                        for item in content:
                            if isinstance(item, dict):
                                # Already in correct format
                                normalized_content.append(item)
                            elif isinstance(item, str):
                                # Convert string to text block
                                normalized_content.append({"type": "text", "text": item})
                            else:
                                # Try to convert Pydantic model to dict
                                if hasattr(item, 'model_dump'):
                                    normalized_content.append(item.model_dump(exclude_unset=True))
                                else:
                                    normalized_content.append(item)
                        normalized_msg["content"] = normalized_content
                    
                    normalized_messages.append(normalized_msg)
                anthropic_request["messages"] = normalized_messages
            
            # Update model to actual provider model (use the actual model name from provider config, not the Anthropic model name)
            original_model = anthropic_request.get("model", "unknown")
            anthropic_request["model"] = actual_model
            
            # Normalize system field format if present
            # Some APIs may require system to be in array format
            if "system" in anthropic_request and anthropic_request["system"] is not None:
                system = anthropic_request["system"]
                # If system is a string, keep it as is (most APIs accept string format)
                # If it's a list, ensure proper structure
                if isinstance(system, list):
                    normalized_system = []
                    for item in system:
                        if isinstance(item, dict):
                            normalized_system.append(item)
                        elif isinstance(item, str):
                            normalized_system.append({"type": "text", "text": item})
                        else:
                            if hasattr(item, 'model_dump'):
                                normalized_system.append(item.model_dump(exclude_unset=True))
                            else:
                                normalized_system.append(item)
                    anthropic_request["system"] = normalized_system
            
            # Remove stream field from request payload if present (it's handled separately)
            # Some APIs may not accept this field in the request body
            if "stream" in anthropic_request:
                del anthropic_request["stream"]
            
            # Remove provider field if present (it's for internal routing only)
            if "provider" in anthropic_request:
                del anthropic_request["provider"]
            
            # Remove fields that may not be supported by all APIs or may cause issues
            # These fields are optional and some APIs may reject requests with unsupported fields
            # Only remove if they are None or empty to avoid breaking APIs that do support them
            fields_to_remove_if_none = [
                "metadata",  # Some APIs don't support metadata
                "container",  # Some APIs don't support container
                "context_management",  # Some APIs don't support context_management
                "mcp_servers",  # Some APIs don't support mcp_servers
                "service_tier",  # Some APIs don't support service_tier
                "thinking",  # Some APIs don't support thinking
            ]

            for field in fields_to_remove_if_none:
                if field in anthropic_request:
                    value = anthropic_request[field]
                    # Remove if None, empty dict, or empty list
                    if value is None or value == {} or value == []:
                        del anthropic_request[field]
                        logger.debug(f"Removed empty/None field '{field}' from request to {provider_config.name}")

            # Validate and fix thinking parameter
            # Some APIs (like qwen-anthropic) have strict requirements for thinking.budget
            if "thinking" in anthropic_request and anthropic_request["thinking"]:
                thinking_dict = anthropic_request["thinking"]
                if isinstance(thinking_dict, dict):
                    # Check for budget field (may be named "budget" or "thinking_budget")
                    budget_value = None
                    budget_key = None

                    if "budget" in thinking_dict:
                        budget_value = thinking_dict["budget"]
                        budget_key = "budget"
                    elif "thinking_budget" in thinking_dict:
                        budget_value = thinking_dict["thinking_budget"]
                        budget_key = "thinking_budget"

                    # Validate budget value
                    if budget_key and budget_value is not None:
                        # Convert to int if it's a string
                        if isinstance(budget_value, str):
                            try:
                                budget_value = int(budget_value)
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid thinking budget value '{budget_value}', removing it")
                                del thinking_dict[budget_key]
                                budget_value = None

                        # Check if budget is a valid positive integer not exceeding 81920
                        if budget_value is not None:
                            try:
                                budget_int = int(budget_value)
                                if budget_int <= 0 or budget_int > 81920:
                                    logger.warning(
                                        f"Invalid thinking budget value {budget_int} (must be 1-81920), "
                                        f"removing it for provider {provider_config.name}"
                                    )
                                    del thinking_dict[budget_key]
                            except (ValueError, TypeError):
                                logger.warning(
                                    f"Invalid thinking budget value '{budget_value}', removing it"
                                )
                                del thinking_dict[budget_key]

                    # If thinking dict becomes empty after validation, remove it
                    if not thinking_dict:
                        del anthropic_request["thinking"]
                        logger.debug(f"Removed empty thinking field after validation")
            
            logger.info(
                f"Anthropic direct request for {provider_config.name}: "
                f"mapped model '{original_model}' -> '{actual_model}', "
                f"payload_keys={list(anthropic_request.keys())}"
            )
            
            # Log messages format for debugging
            if "messages" in anthropic_request and anthropic_request["messages"]:
                first_msg = anthropic_request["messages"][0]
                logger.debug(
                    f"First message format: role={first_msg.get('role')}, "
                    f"content_type={type(first_msg.get('content')).__name__}, "
                    f"content={first_msg.get('content')}"
                )
            
            logger.debug(f"Full anthropic_request: {json.dumps(anthropic_request, ensure_ascii=False, indent=2)}")
            
            # Make request
            if req.stream:
                # For streaming requests, don't close client here - it will be closed in the generator
                return await self._handle_anthropic_streaming_request(
                    anthropic_request, provider_config, actual_model, client, request_id, start_time
                )
            else:
                # For non-streaming requests, close client after request completes
                try:
                    return await self._handle_anthropic_non_streaming_request(
                        anthropic_request, provider_config, actual_model, client, request_id, start_time
                    )
                finally:
                    # Close client after non-streaming request completes
                    await client.close_async()
        except httpx.HTTPStatusError as e:
            error_text = str(e.response.text) if hasattr(e.response, 'text') else ""
            logger.error(f"HTTP error from {provider_config.name}: {e.response.status_code} - {error_text}")
            # Close client on error for non-streaming requests
            if not req.stream:
                try:
                    await client.close_async()
                except:
                    pass
            # Re-raise HTTPStatusError so it can be handled by the main loop
            # This allows 4xx errors to be treated as model failures for fallback handling
            raise e
        except httpx.RequestError as e:
            logger.error(f"Request error from {provider_config.name}: {e}")
            # Close client on error for non-streaming requests
            if not req.stream:
                try:
                    await client.close_async()
                except:
                    pass
            raise HTTPException(
                status_code=503,
                detail={
                    "type": "connection_error",
                    "message": f"Connection error to provider '{provider_config.name}': {str(e)}",
                    "provider": provider_config.name
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error from {provider_config.name}: {e}", exc_info=True)
            # Close client on error for non-streaming requests
            if not req.stream:
                try:
                    await client.close_async()
                except:
                    pass
            raise HTTPException(
                status_code=500,
                detail={
                    "type": "internal_error",
                    "message": f"Internal error: {str(e)}",
                    "provider": provider_config.name
                }
            )
    
    async def _handle_anthropic_streaming_request(
        self,
        anthropic_request: dict,
        provider_config,
        actual_model: str,
        client: AnthropicClient,
        request_id: str,
        start_time: float
    ) -> StreamingResponse:
        """Handle streaming Anthropic direct request."""
        async def generate():
            chunk_count = 0
            try:
                async for chunk in client.messages_async(anthropic_request, stream=True):
                    chunk_count += 1
                    json_str = json.dumps(chunk, ensure_ascii=False, separators=(',', ':'))
                    event_type = chunk.get("type", "")
                    # 使用标准的SSE格式，包含event和data字段，与OpenAI转换路径保持一致
                    if event_type:
                        yield f"event: {event_type}\ndata: {json_str}\n\n"
                    else:
                        yield f"data: {json_str}\n\n"

                # Check if we received any chunks - if not, this might indicate a problem
                if chunk_count == 0:
                    logger.warning(
                        f"Streaming request to {provider_config.name} completed without any chunks. "
                        f"Model: {actual_model}, Request ID: {request_id}"
                    )
                    # Even if no chunks were received, we should still send message_stop
                    # to properly close the stream, but log it for debugging

                # 使用标准的message_stop事件代替[DONE]标记
                # 保持与SSE格式的一致性
                yield f"event: message_stop\ndata: {{\"type\": \"message_stop\"}}\n\n"
            except Exception as e:
                logger.error(f"Error in streaming response from {provider_config.name}: {e}", exc_info=True)
                # 标准化错误响应格式，符合Claude客户端期望
                error_response = {
                    "type": "error",
                    "error": {
                        "type": "api_error",
                        "message": str(e),
                        "code": "streaming_error"
                    }
                }
                yield f"event: error\ndata: {json.dumps(error_response)}\n\n"
                # 立即发送message_stop确保连接终止
                yield f"event: message_stop\ndata: {{\"type\": \"message_stop\"}}\n\n"
            finally:
                # Close client after streaming completes (or on error)
                try:
                    await client.close_async()
                except Exception as close_error:
                    logger.debug(f"Error closing client for {provider_config.name}: {close_error}")
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
    
    async def _handle_anthropic_non_streaming_request(
        self,
        anthropic_request: dict,
        provider_config,
        actual_model: str,
        client: AnthropicClient,
        request_id: str,
        start_time: float
    ) -> dict:
        """Handle non-streaming Anthropic direct request."""
        # Make request
        async def make_request():
            # For non-streaming, messages_async yields a single response
            async for response in client.messages_async(anthropic_request, stream=False):
                return response
            # Should not reach here, but just in case
            raise ValueError("No response received from provider")
        
        response = await retry_with_backoff(
            make_request,
            max_retries=provider_config.max_retries,
            initial_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            retryable_exceptions=(httpx.ReadTimeout, httpx.TimeoutException, httpx.ConnectTimeout, httpx.PoolTimeout, httpx.RequestError),
            provider_name=provider_config.name
        )
        
        # Log to database
        usage = response.get("usage", {})
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        
        db = get_database()
        await db.log_request(
            request_id=request_id,
            provider_name=provider_config.name,
            model=actual_model,
            request_params=anthropic_request,
            response_data=response,
            status_code=200,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            response_time_ms=(time.time() - start_time) * 1000
        )
        
        # Update token usage statistics
        if input_tokens or output_tokens:
            today = datetime.now().strftime("%Y-%m-%d")
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
        
        return response
    
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

