"""OpenAI format message handler."""
import asyncio
import json
import logging
import time
import unicodedata
from typing import Any, Dict

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from openai import RateLimitError, APIError, APIConnectionError
import httpx

from .base import BaseRequestHandler
from ...config import config
from ...core import MessagesRequest, Message, ModelManager, COST_PER_INPUT_TOKEN, COST_PER_OUTPUT_TOKEN, COLOR_GREEN, COLOR_YELLOW, COLOR_RESET
from ...converters import to_openai, to_anthropic, to_anthropic_async
from ...infrastructure import OpenAIClient, retry_with_backoff, get_cache_manager
from ...utils import openai_response_to_dict
from ..token_counter import count_tokens_estimate
from ...utils.token_extractor import extract_tokens_from_usage

logger = logging.getLogger(__name__)


def calculate_display_width(text):
    """Calculate the actual display width of text considering Unicode characters."""
    width = 0
    for char in str(text):
        eaw = unicodedata.east_asian_width(char)
        if eaw in ('F', 'W'):
            width += 2
        elif eaw in ('H', 'Na', 'N'):
            width += 1
        else:
            width += 1
    return width


def _validate_max_tokens(
    openai_request: Dict[str, Any],
    provider_config = None,
    model: str = None
) -> None:
    """Validate and normalize OpenAI request parameters.

    Args:
        openai_request: The OpenAI-format request dict
        provider_config: Provider configuration (optional)
        model: The actual model name (optional)
    """
    max_tokens = openai_request.get("max_tokens")
    if max_tokens is None:
        return

    original_max_tokens = max_tokens
    max_tokens = max(max_tokens, config.min_tokens_limit)
    max_tokens = min(max_tokens, config.max_tokens_limit)

    provider_max_limit = None
    if provider_config and hasattr(provider_config, 'name'):
        provider_name = provider_config.name.lower()

        if 'qwen' in provider_name:
            if model:
                model_lower = model.lower()
                if 'coder-plus' in model_lower or 'qwen3' in model_lower:
                    provider_max_limit = 65536
                elif 'flash' in model_lower:
                    provider_max_limit = 32768
                else:
                    provider_max_limit = 32768
            else:
                provider_max_limit = 32768

        if hasattr(provider_config, 'max_tokens_limit') and provider_config.max_tokens_limit:
            provider_max_limit = min(provider_max_limit or float('inf'), provider_config.max_tokens_limit)

    if provider_max_limit:
        max_tokens = min(max_tokens, provider_max_limit)

    openai_request["max_tokens"] = int(max_tokens)

    if original_max_tokens != max_tokens:
        limit_info = f"global limits: min={config.min_tokens_limit}, max={config.max_tokens_limit}"
        if provider_max_limit:
            limit_info += f", provider limit: {provider_max_limit}"
        logger.debug(f"Limited max_tokens from {original_max_tokens} to {max_tokens} ({limit_info})")


def _filter_unsupported_params(
    provider_config,
    openai_request: Dict[str, Any]
) -> None:
    """Filter out potentially unsupported parameters for specific providers.

    Args:
        provider_config: Provider configuration
        openai_request: The request dict to modify in place
    """
    unsupported_params = []

    if provider_config.name == "modelscope":
        if "tool_choice" in openai_request:
            tool_choice_val = openai_request.pop("tool_choice")
            unsupported_params.append(f"tool_choice={tool_choice_val}")

        if "enable_thinking" in openai_request:
            enable_thinking = openai_request.pop("enable_thinking")
            if enable_thinking:
                unsupported_params.append(f"enable_thinking={enable_thinking} (removed, must be false for non-streaming)")

        for msg in openai_request.get("messages", []):
            if msg.get("role") == "assistant":
                if "tool_calls" in msg and msg.get("content") is None:
                    msg["content"] = ""
                elif "tool_calls" in msg and not msg.get("content"):
                    msg["content"] = ""
            elif msg.get("role") == "tool":
                if not msg.get("content"):
                    msg["content"] = "No result"

        if unsupported_params:
            logger.debug(f"Filtered unsupported parameters for {provider_config.name}: {', '.join(unsupported_params)}")


class OpenAIMessageHandler(BaseRequestHandler):
    """Handler for OpenAI-format API requests.

    Handles streaming and non-streaming requests for providers that use
    the OpenAI API format.
    """

    def __init__(self, model_manager: ModelManager):
        """Initialize the OpenAI message handler.

        Args:
            model_manager: The model manager instance
        """
        super().__init__(model_manager)

    def _filter_unsupported_params(self, provider_config, openai_request: dict):
        """Filter out potentially unsupported parameters for specific providers.

        Args:
            provider_config: Provider configuration
            openai_request: The request dict to modify in place
        """
        _filter_unsupported_params(provider_config, openai_request)

    def _validate_max_tokens(self, openai_request: dict, provider_config=None, actual_model: str = None):
        """Validate and limit max_tokens.

        Args:
            openai_request: The request dict
            provider_config: Provider configuration (optional)
            actual_model: The actual model name (optional)
        """
        _validate_max_tokens(openai_request, provider_config, actual_model)

    def _convert_request(self, req: MessagesRequest) -> dict:
        """Convert Anthropic request to OpenAI format.

        Args:
            req: The Anthropic-format request

        Returns:
            OpenAI-format request dict
        """
        return to_openai(req)

    def _convert_response(self, openai_response, original_model: str) -> dict:
        """Convert OpenAI response to Anthropic format.

        Args:
            openai_response: The OpenAI response
            original_model: Original model name

        Returns:
            Anthropic-format response dict
        """
        return to_anthropic(openai_response, original_model)

    def _convert_response_async(self, openai_stream, original_model: str, input_tokens: int):
        """Convert OpenAI streaming response to Anthropic streaming format.

        Args:
            openai_stream: Async iterator of OpenAI streaming chunks
            original_model: Original model name
            input_tokens: Input token count for the request

        Returns:
            Async iterator of Anthropic-format streaming chunks
        """
        return to_anthropic_async(openai_stream, original_model, input_tokens)

    async def _log_modelscope_error(self, api_params: dict, actual_model: str):
        """Log detailed error information for modelscope provider."""
        logger.error(f"Request details for modelscope: model={actual_model}, "
                   f"max_tokens={api_params.get('max_tokens')}, "
                   f"has_tools={bool(api_params.get('tools'))}, "
                   f"message_count={len(api_params.get('messages', []))}, "
                   f"has_tool_choice={'tool_choice' in api_params}")
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
            if "content" in msg:
                content = msg.get("content")
                if isinstance(content, str):
                    msg_info["content_preview"] = content[:100] if len(content) > 100 else content
                elif isinstance(content, list):
                    msg_info["content_preview"] = f"list[{len(content)} items]"
                else:
                    msg_info["content_preview"] = str(content)[:100]
            logger.debug(f"Message {idx}: {json_module.dumps(msg_info, ensure_ascii=False)}")

    async def handle_streaming(
        self,
        req: MessagesRequest,
        provider_config,
        actual_model: str,
        request_id: str,
        start_time: float
    ) -> StreamingResponse:
        """Handle streaming OpenAI-format request.

        Args:
            req: The request object
            provider_config: Provider configuration
            actual_model: The actual model name to use
            request_id: Unique request identifier
            start_time: Request start time

        Returns:
            StreamingResponse
        """
        # Convert request to OpenAI format
        openai_request = self._convert_request(req)

        # Filter unsupported params and validate max_tokens
        self._filter_unsupported_params(provider_config, openai_request)
        self._validate_max_tokens(openai_request, provider_config, actual_model)

        client = OpenAIClient(provider_config)

        async def generate():
            try:
                # Build API params
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
                if "tool_choice" in openai_request:
                    api_params["tool_choice"] = openai_request["tool_choice"]

                # Estimate input tokens (as fallback if actual usage not available)
                messages_list = []
                for msg in req.messages:
                    if isinstance(msg, Message):
                        messages_list.append({
                            "role": msg.role.value,
                            "content": msg.content
                        })
                    else:
                        messages_list.append(msg)
                initial_input_tokens = count_tokens_estimate(messages_list, actual_model)

                max_retries = provider_config.max_retries
                retry_count = 0

                while retry_count <= max_retries:
                    try:
                        async def make_stream_request():
                            return await client.chat_completion_async(**api_params)

                        openai_stream = await retry_with_backoff(
                            make_stream_request,
                            max_retries=0,
                            provider_name=provider_config.name
                        )

                        if openai_stream is None:
                            logger.error(f"Received None stream from {provider_config.name}")
                            raise ValueError(f"Stream from {provider_config.name} is None")

                        actual_provider = None

                        async def stream_iterator():
                            async for chunk in openai_stream:
                                yield chunk

                        chunk_count = 0
                        # Track actual usage from converter output
                        actual_usage = None
                        actual_input_tokens = None
                        actual_output_tokens = None
                        try:
                            async for chunk in self._convert_response_async(
                                stream_iterator(), req.model, initial_input_tokens
                            ):
                                chunk_count += 1

                                if chunk.get("type") == "message_metadata" and not actual_provider:
                                    actual_provider = chunk.get("actual_provider")
                                    logger.debug(f"Received actual_provider from metadata: {actual_provider}")
                                    continue

                                # Extract actual usage from message_delta event
                                if chunk.get("type") == "message_delta":
                                    chunk_usage = chunk.get("usage")
                                    if chunk_usage:
                                        actual_usage = chunk_usage
                                        actual_input_tokens, actual_output_tokens = extract_tokens_from_usage(chunk_usage)
                                        logger.debug(f"Received actual usage: input={actual_input_tokens}, output={actual_output_tokens}")

                                json_str = json.dumps(chunk, ensure_ascii=False, separators=(',', ':'), sort_keys=False)
                                event_type = chunk.get("type", "")
                                if event_type:
                                    yield f"event: {event_type}\ndata: {json_str}\n\n"
                                else:
                                    yield f"data: {json_str}\n\n"
                        except Exception as stream_error:
                            logger.error(f"Error iterating stream: {stream_error}", exc_info=True)
                            raise

                        if chunk_count == 0:
                            logger.warning(
                                f"Streaming request to {provider_config.name} (OpenAI format) completed without any chunks. "
                                f"Model: {actual_model}, Request ID: {request_id}"
                            )
                            yield f"event: message_stop\ndata: {{\"type\": \"message_stop\"}}\n\n"

                        # Use actual usage if available, otherwise fall back to estimate
                        final_input_tokens = actual_input_tokens if actual_input_tokens is not None else initial_input_tokens
                        final_output_tokens = actual_output_tokens if actual_output_tokens is not None else 0

                        # Log success
                        import datetime
                        response_time_ms = (time.time() - start_time) * 1000
                        provider_width = calculate_display_width(actual_provider or provider_config.name)
                        total_width = 35
                        padding_needed = total_width - provider_width - 4
                        padding = " " * padding_needed
                        usage_source = "actual" if actual_usage else "estimate"
                        end_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                        logger.info(
                            f"[Request {request_id}] {COLOR_GREEN}Streaming completed at{COLOR_RESET} {COLOR_YELLOW}{end_timestamp}{COLOR_RESET}\n"
                            f"[Request {request_id}] Streaming summary:\n"
                            f"  Provider: {provider_config.name}\n"
                            f"  {COLOR_GREEN}┌──────── Actual Provider ────────┐{COLOR_RESET}\n"
                            f"  {COLOR_GREEN}│ {actual_provider or provider_config.name}{padding} │{COLOR_RESET}\n"
                            f"  {COLOR_GREEN}└─────────────────────────────────┘{COLOR_RESET}\n"
                            f"  Model: {actual_model}\n"
                            f"  Input Tokens: {final_input_tokens} ({usage_source})\n"
                            f"  Output Tokens: {final_output_tokens} ({usage_source})\n"
                            f"  Response Time: {response_time_ms:.2f}ms\n"
                            f"  Chunks Sent: {chunk_count}"
                        )

                        await self._log_request(
                            request_id=request_id,
                            provider_name=provider_config.name,
                            model=actual_model,
                            request_params=openai_request,
                            status_code=200,
                            input_tokens=final_input_tokens,
                            output_tokens=final_output_tokens,
                            response_time_ms=response_time_ms
                        )

                        cost_estimate = final_input_tokens * COST_PER_INPUT_TOKEN + final_output_tokens * COST_PER_OUTPUT_TOKEN
                        await self._update_token_usage(
                            provider_config.name, actual_model, final_input_tokens, final_output_tokens, cost_estimate
                        )

                        break

                    except (httpx.ReadTimeout, httpx.TimeoutException, httpx.ConnectTimeout, httpx.PoolTimeout, APIConnectionError) as e:
                        retry_count += 1
                        if retry_count <= max_retries:
                            delay = min(1.0 * (2.0 ** (retry_count - 1)), 60.0)
                            error_type = "connection_timeout" if isinstance(e, (httpx.ConnectTimeout, httpx.PoolTimeout)) else \
                                         "read_timeout" if isinstance(e, (httpx.ReadTimeout, httpx.TimeoutException)) else \
                                         "connection_error"
                            logger.warning(f"Streaming error ({error_type}) for {provider_config.name}, retry {retry_count}/{max_retries}")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': {'type': 'connection_error', 'message': str(e)}})}\n\n"
                            raise

            except Exception as e:
                logger.error(f"Unexpected error in streaming: {e}", exc_info=True)
                error_response = {
                    "type": "error",
                    "error": {
                        "type": "internal_error",
                        "message": f"Internal error: {str(e)}",
                        "provider": provider_config.name
                    }
                }
                yield f"event: error\ndata: {json.dumps(error_response)}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    async def handle_non_streaming(
        self,
        req: MessagesRequest,
        provider_config,
        actual_model: str,
        request_id: str,
        start_time: float
    ) -> dict:
        """Handle non-streaming OpenAI-format request.

        Args:
            req: The request object
            provider_config: Provider configuration
            actual_model: The actual model name to use
            request_id: Unique request identifier
            start_time: Request start time

        Returns:
            Anthropic-format response dict
        """
        # Convert request to OpenAI format
        openai_request = self._convert_request(req)

        # Filter unsupported params and validate max_tokens
        self._filter_unsupported_params(provider_config, openai_request)
        self._validate_max_tokens(openai_request, provider_config, actual_model)

        client = OpenAIClient(provider_config)

        try:
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
            if "tool_choice" in openai_request:
                api_params["tool_choice"] = openai_request["tool_choice"]
            if "enable_thinking" in openai_request:
                del openai_request["enable_thinking"]
            if "enable_thinking" in api_params:
                del api_params["enable_thinking"]

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
                    "message": f"Unable to connect to provider '{provider_config.name}'. Connection timeout.",
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
                    "message": f"Request timeout for provider '{provider_config.name}'.",
                    "provider": provider_config.name
                }
            )
        except APIError as e:
            error_detail = str(e)
            logger.error(f"API error from provider {provider_config.name}: {e}")
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
            logger.error(f"Failed to convert response from {provider_config.name}: {e}", exc_info=True)
            raise HTTPException(
                status_code=502,
                detail={
                    "type": "api_error",
                    "message": f"Failed to process response from provider '{provider_config.name}': {str(e)}",
                    "provider": provider_config.name
                }
            )

        if not isinstance(openai_dict, dict):
            logger.error(f"Invalid response type from {provider_config.name}: {type(openai_dict)}")
            raise HTTPException(
                status_code=502,
                detail={
                    "type": "api_error",
                    "message": f"Invalid response format from provider '{provider_config.name}'",
                    "provider": provider_config.name
                }
            )

        choices = openai_dict.get('choices')

        if choices is None or (isinstance(choices, list) and len(choices) == 0):
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

            logger.error(f"Invalid response from {provider_config.name}: choices is None or empty")
            raise HTTPException(
                status_code=502,
                detail={
                    "type": "api_error",
                    "message": f"Provider '{provider_config.name}' returned an invalid response",
                    "provider": provider_config.name,
                    "model": actual_model
                }
            )

        # Cache response if enabled
        cache_enabled = config.app_config.cache.enabled
        if cache_enabled:
            cache_manager = get_cache_manager()
            cache_key = f"response:{provider_config.name}:{actual_model}:{hash(json.dumps(openai_request, sort_keys=True))}"
            await cache_manager.set(cache_key, openai_dict, ttl=config.app_config.cache.default_ttl)

        # Convert to Anthropic format
        anthropic_response = self._convert_response(openai_dict, req.model)

        # Extract token usage using unified extractor
        # 先尝试从转换后的 Anthropic 响应获取
        input_tokens, output_tokens = extract_tokens_from_usage(anthropic_response.get("usage"))

        # 如果没有获取到或为0，再从原始 OpenAI 响应获取
        if (input_tokens is None or output_tokens is None or
            (input_tokens == 0 and output_tokens == 0 and openai_dict.get('usage'))):
            openai_input, openai_output = extract_tokens_from_usage(openai_dict.get('usage'))
            input_tokens = input_tokens or openai_input
            output_tokens = output_tokens or openai_output

        # 确保有默认值
        input_tokens = input_tokens if input_tokens is not None else 0
        output_tokens = output_tokens if output_tokens is not None else 0

        # Log and update stats
        response_time_ms = (time.time() - start_time) * 1000
        await self._log_request(
            request_id=request_id,
            provider_name=provider_config.name,
            model=actual_model,
            request_params=openai_request,
            response_data=anthropic_response,
            status_code=200,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            response_time_ms=response_time_ms
        )

        if input_tokens or output_tokens:
            cost_estimate = (input_tokens or 0) * COST_PER_INPUT_TOKEN + (output_tokens or 0) * COST_PER_OUTPUT_TOKEN
            await self._update_token_usage(
                provider_config.name, actual_model, input_tokens or 0, output_tokens or 0, cost_estimate
            )

        # Log completion for non-streaming
        import datetime
        provider_width = calculate_display_width(provider_config.name)
        total_width = 35
        padding_needed = total_width - provider_width - 4
        padding = " " * padding_needed
        end_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        logger.info(
            f"[Request {request_id}] {COLOR_GREEN}Non-streaming completed at{COLOR_RESET} {COLOR_YELLOW}{end_timestamp}{COLOR_RESET}\n"
            f"[Request {request_id}] Response summary:\n"
            f"  Provider: {provider_config.name}\n"
            f"  {COLOR_GREEN}┌──────── Actual Provider ────────┐{COLOR_RESET}\n"
            f"  {COLOR_GREEN}│ {provider_config.name}{padding} │{COLOR_RESET}\n"
            f"  {COLOR_GREEN}└─────────────────────────────────┘{COLOR_RESET}\n"
            f"  Model: {actual_model}\n"
            f"  Input Tokens: {input_tokens}\n"
            f"  Output Tokens: {output_tokens}\n"
            f"  Response Time: {response_time_ms:.2f}ms"
        )

        return anthropic_response
