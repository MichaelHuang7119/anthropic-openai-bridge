"""Anthropic format message handler."""
import json
import logging
import time
import unicodedata
from typing import Any, Dict

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import httpx

from .base import BaseRequestHandler
from ...core import MessagesRequest, ModelManager, COST_PER_INPUT_TOKEN, COST_PER_OUTPUT_TOKEN, COLOR_GREEN, COLOR_YELLOW, COLOR_RESET, COLOR_CYAN
from ...infrastructure import AnthropicClient, retry_with_backoff
from ..token_counter import count_tokens_estimate
from ...utils.token_extractor import extract_tokens_from_usage, update_token_tracking

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


def _normalize_request(req: Any) -> Dict[str, Any]:
    """Normalize Anthropic-format request for direct forwarding.

    Args:
        req: The request object (MessagesRequest or dict)

    Returns:
        Normalized Anthropic-format request dict
    """
    if isinstance(req, dict):
        anthropic_request = req.copy()
    else:
        anthropic_request = req.model_dump(exclude_none=True, exclude_unset=True)

    # Normalize messages content format
    if "messages" in anthropic_request:
        normalized_messages = []
        for msg in anthropic_request["messages"]:
            normalized_msg = msg.copy() if isinstance(msg, dict) else dict(msg)
            content = normalized_msg.get("content")

            if isinstance(content, str):
                normalized_msg["content"] = [{"type": "text", "text": content}]
            elif isinstance(content, list):
                normalized_content = []
                for item in content:
                    if isinstance(item, dict):
                        normalized_content.append(item)
                    elif isinstance(item, str):
                        normalized_content.append({"type": "text", "text": item})
                    else:
                        if hasattr(item, 'model_dump'):
                            normalized_content.append(item.model_dump(exclude_unset=True))
                        else:
                            normalized_content.append(item)
                normalized_msg["content"] = normalized_content
            normalized_messages.append(normalized_msg)
        anthropic_request["messages"] = normalized_messages

    # Normalize system field format
    if "system" in anthropic_request and anthropic_request["system"] is not None:
        system = anthropic_request["system"]
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

    # Remove unsupported fields for some APIs
    fields_to_remove_if_none = [
        "metadata", "container", "context_management",
        "mcp_servers", "service_tier", "thinking",
    ]
    for field in fields_to_remove_if_none:
        if field in anthropic_request:
            value = anthropic_request[field]
            if value is None or value == {} or value == []:
                del anthropic_request[field]
                logger.debug(f"Removed empty/None field '{field}'")

    # Validate thinking parameter
    if "thinking" in anthropic_request and anthropic_request["thinking"]:
        thinking_dict = anthropic_request["thinking"]
        if isinstance(thinking_dict, dict):
            budget_key = "budget" if "budget" in thinking_dict else "thinking_budget"
            if budget_key in thinking_dict:
                budget_value = thinking_dict[budget_key]
                try:
                    if isinstance(budget_value, str):
                        budget_value = int(budget_value)
                    if budget_value <= 0 or budget_value > 81920:
                        del thinking_dict[budget_key]
                except (ValueError, TypeError):
                    del thinking_dict[budget_key]
            if not thinking_dict:
                del anthropic_request["thinking"]

    return anthropic_request


def _handle_thinking_from_streaming_text(
    chunk: dict,
    reasoning_flag: bool,
    total_output_tokens: int
) -> tuple:
    """Process thinking blocks from streaming chunks.

    Handles various thinking tags and converts them to Anthropic-format
    content_block_delta events with thinking_delta type.

    Supports multiple thinking tag formats for different AI models:
    - <thinking>/</thinking>
    - <think>/</think>
    - <reason>/</reason>
    - <reasoning>/</reasoning>
    - <thought>/</thought>
    - <Thought>/</Thought>
    - <|begin_of_thought|>/<|end_of_thought|>
    - ◁think▷/◁/think▷
    - 【Thinking】/【/Thinking】

    Args:
        chunk: The streaming chunk dict
        reasoning_flag: Current thinking state flag
        total_output_tokens: Current output token count

    Returns:
        Tuple of (events, new_reasoning_flag, new_total_output_tokens, should_continue)
        - events: List of SSE event strings to yield
        - new_reasoning_flag: Updated reasoning state
        - new_total_output_tokens: Updated token count
        - should_continue: Whether to skip normal chunk processing
    """
    events = []
    delta = chunk.get("delta", {})
    text = delta.get("text", "")

    new_reasoning_flag = reasoning_flag
    new_total_output_tokens = total_output_tokens
    should_continue = False

    if not text:
        return events, new_reasoning_flag, new_total_output_tokens, should_continue

    # Define supported thinking tag pairs
    thinking_tags = [
        ("<thinking>", "</thinking>"),
        ("<think>", "</think>"),
        ("<reason>", "</reason>"),
        ("<reasoning>", "</reasoning>"),
        ("<thought>", "</thought>"),
        ("<Thought>", "</Thought>"),
        ("<|begin_of_thought|>", "<|end_of_thought|>"),
        ("◁think▷", "◁/think▷"),
        ("【Thinking】", "【/Thinking】"),
    ]

    # Find which tags are present in the text
    matched_tags = None
    for start_tag, end_tag in thinking_tags:
        start_idx = text.find(start_tag)
        end_idx = text.find(end_tag)
        if start_idx != -1 or end_idx != -1:
            matched_tags = (start_tag, end_tag, start_idx, end_idx)
            break

    if not matched_tags and not reasoning_flag:
        # No thinking tags and not in thinking mode, return as-is
        return events, new_reasoning_flag, new_total_output_tokens, should_continue

    if matched_tags:
        start_tag, end_tag, start_idx, end_idx = matched_tags
    else:
        # In thinking mode but no new tags, continue with first tag format
        start_tag, end_tag = thinking_tags[0]
        start_idx = -1
        end_idx = -1

    # Process thinking tags
    thinking_content = None
    remaining_text = text

    if start_idx != -1 or end_idx != -1 or reasoning_flag:
        new_reasoning_flag = True

        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            # Complete thinking block in this chunk
            if start_idx == 0:
                thinking_content = text[len(start_tag):end_idx]
            else:
                # Regular text before thinking block
                chunk["delta"]["text"] = text[:start_idx]
                thinking_content = text[start_idx + len(start_tag):end_idx]
                remaining_text = text[end_idx + len(end_tag):]
            new_reasoning_flag = False
        elif start_idx != -1:
            # Thinking block starts
            if start_idx == 0:
                remaining_text = text[len(start_tag):]
            else:
                chunk["delta"]["text"] = text[:start_idx]
                remaining_text = text[start_idx + len(start_tag):]
        elif end_idx != -1:
            # Thinking block ends
            if end_idx == 0:
                thinking_content = ""
            else:
                thinking_content = text[:end_idx]
                remaining_text = text[end_idx + len(end_tag):]
            new_reasoning_flag = False
        elif reasoning_flag and not start_idx and not end_idx:
            # Still in thinking mode, no new tags
            thinking_content = text
            remaining_text = ""

        # Emit thinking delta event
        if thinking_content is not None and thinking_content:
            thinking_event = {
                "type": "content_block_delta",
                "index": 0,
                "delta": {
                    "type": "thinking_delta",
                    "thinking": thinking_content
                }
            }
            events.append(
                f"event: content_block_delta\n"
                f"data: {json.dumps(thinking_event, ensure_ascii=False, separators=(',', ':'))}\n\n"
            )
            new_total_output_tokens += len(thinking_content.split())

        # Update chunk text
        if remaining_text:
            chunk["delta"]["text"] = remaining_text
        else:
            should_continue = True

    return events, new_reasoning_flag, new_total_output_tokens, should_continue


class AnthropicMessageHandler(BaseRequestHandler):
    """Handler for Anthropic-format API requests.

    Handles streaming and non-streaming requests for providers that use
    the Anthropic API format directly.
    """

    def __init__(self, model_manager: ModelManager):
        """Initialize the Anthropic message handler.

        Args:
            model_manager: The model manager instance
        """
        super().__init__(model_manager)

    def _prepare_request(self, req: MessagesRequest) -> dict:
        """Prepare Anthropic-format request for direct forwarding.

        Args:
            req: The request object (MessagesRequest or dict)

        Returns:
            Prepared Anthropic-format request dict
        """
        return _normalize_request(req)

    def _extract_usage_from_response(self, response: dict) -> tuple:
        """Extract token usage from Anthropic response.

        Args:
            response: The response dict

        Returns:
            Tuple of (input_tokens, output_tokens)
        """
        # Handle case where usage key might be None instead of missing
        usage_raw = response.get("usage")
        usage = usage_raw if isinstance(usage_raw, dict) else {}
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        return input_tokens, output_tokens

    async def handle_streaming(
        self,
        req: MessagesRequest,
        provider_config,
        actual_model: str,
        request_id: str,
        start_time: float
    ) -> StreamingResponse:
        """Handle streaming Anthropic-format request.

        Args:
            req: The request object
            provider_config: Provider configuration
            actual_model: The actual model name to use
            request_id: Unique request identifier
            start_time: Request start time

        Returns:
            StreamingResponse
        """
        # Prepare request
        anthropic_request = self._prepare_request(req)
        original_model = anthropic_request.get("model", "unknown")
        anthropic_request["model"] = actual_model

        logger.info(
            f"Anthropic direct request for {provider_config.name}: "
            f"mapped model '{original_model}' -> '{actual_model}'"
        )

        client = AnthropicClient(provider_config)

        async def generate():
            chunk_count = 0
            total_output_tokens = 0
            total_input_tokens = 0
            messages = anthropic_request.get("messages", [])
            initial_input_tokens = count_tokens_estimate(messages, actual_model)
            reasoning_flag = False
            # Track provider_message_id
            actual_message_id = None
            # Track actual provider name from API response
            actual_provider = None

            try:
                async for chunk in client.messages_async(anthropic_request, stream=True):
                    logger.debug(f"Anthropic streaming: {chunk}")
                    chunk_count += 1

                    # Extract actual provider name from chunk
                    if not actual_provider and isinstance(chunk, dict) and chunk.get("provider"):
                        actual_provider = chunk.get("provider")
                        logger.debug(f"Extracted actual provider: {actual_provider}")

                    # Extract actual_message_id from chunk
                    # For Anthropic, the id is in message_start event's message object
                    if not actual_message_id and isinstance(chunk, dict):
                        if chunk.get("type") == "message_start" and isinstance(chunk.get("message"), dict):
                            actual_message_id = chunk.get("message", {}).get("id")
                        elif chunk.get("id"):
                            # Fallback to direct id if available
                            actual_message_id = chunk.get("id")

                        if actual_message_id:
                            logger.debug(f"Extracted actual provider_message_id: {actual_message_id}")

                    # Extract usage from chunk (message_start, message_delta events)
                    chunk_usage = chunk.get("usage") if isinstance(chunk, dict) else None
                    if chunk_usage:
                        # 使用统一的 token 提取工具，支持多种 API 格式
                        actual_input, actual_output = extract_tokens_from_usage(chunk_usage)
                        if actual_input is not None:
                            total_input_tokens = actual_input
                        if actual_output is not None:
                            total_input_tokens, total_output_tokens = update_token_tracking(
                                total_input_tokens, total_output_tokens, actual_input, actual_output
                            )

                    # Handle thinking blocks (<thinking> tags)
                    if isinstance(chunk, dict) and chunk.get("type") == "content_block_delta":
                        events, reasoning_flag, total_output_tokens, skip_chunk = _handle_thinking_from_streaming_text(
                            chunk, reasoning_flag, total_output_tokens
                        )
                        for event in events:
                            yield event
                        if skip_chunk:
                            continue

                    json_str = json.dumps(chunk, ensure_ascii=False, separators=(',', ':'), sort_keys=False)
                    event_type = chunk.get("type", "")
                    if event_type:
                        yield f"event: {event_type}\ndata: {json_str}\n\n"
                    else:
                        yield f"data: {json_str}\n\n"

                # Check if we received any chunks
                if chunk_count == 0:
                    logger.warning(
                        f"Streaming request to {provider_config.name} completed without any chunks. "
                        f"Model: {actual_model}, Request ID: {request_id}"
                    )
                    yield f"event: message_stop\ndata: {{\"type\": \"message_stop\"}}\n\n"
                else:
                    # Log success
                    import datetime
                    response_time_ms = (time.time() - start_time) * 1000
                    # Use actual_provider from API response, fallback to provider_config.name
                    display_provider = actual_provider or provider_config.name
                    provider_width = calculate_display_width(display_provider)
                    total_width = 35
                    padding_needed = total_width - provider_width - 4
                    padding = " " * padding_needed
                    # 优先使用实际的 input_tokens，如果没有则使用估算值
                    final_input_tokens = total_input_tokens if total_input_tokens > 0 else initial_input_tokens
                    end_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

                    logger.debug(
                        f"Received actual usage: input={final_input_tokens}, output={total_output_tokens}"
                    )

                    logger.info(
                        f"{COLOR_CYAN}[Request {request_id}]{COLOR_RESET}\n"
                        f"  {COLOR_GREEN}Streaming completed at{COLOR_RESET} {COLOR_YELLOW}{end_timestamp}{COLOR_RESET}\n"
                        f"  API Format: anthropic\n"
                        f"  Stream: True\n"
                        f"  Provider: {provider_config.name}\n"
                        f"  {COLOR_GREEN}┌──────── Actual Provider ────────┐{COLOR_RESET}\n"
                        f"  {COLOR_GREEN}│ {display_provider}{padding} │{COLOR_RESET}\n"
                        f"  {COLOR_GREEN}└─────────────────────────────────┘{COLOR_RESET}\n"
                        f"  Model: {actual_model}\n"
                        f"  Actual Provider Message ID: {actual_message_id}\n"
                        f"  Input Tokens: {final_input_tokens}\n"
                        f"  Output Tokens: {total_output_tokens}\n"
                        f"  Response Time: {response_time_ms:.2f}ms\n"
                        f"  Chunks Sent: {chunk_count}"
                    )

                    await self._log_request(
                        request_id=request_id,
                        provider_name=provider_config.name,
                        model=actual_model,
                        request_params=anthropic_request,
                        status_code=200,
                        input_tokens=final_input_tokens,
                        output_tokens=total_output_tokens,
                        response_time_ms=response_time_ms
                    )

                    cost_estimate = final_input_tokens * COST_PER_INPUT_TOKEN + total_output_tokens * COST_PER_OUTPUT_TOKEN
                    await self._update_token_usage(
                        provider_config.name, actual_model, final_input_tokens, total_output_tokens, cost_estimate
                    )

            except Exception as e:
                logger.error(f"Error in streaming response from {provider_config.name}: {e}", exc_info=True)
                error_response = {
                    "type": "error",
                    "error": {
                        "type": "api_error",
                        "message": str(e),
                        "code": "streaming_error"
                    }
                }
                yield f"event: error\ndata: {json.dumps(error_response)}\n\n"
                yield f"event: message_stop\ndata: {{\"type\": \"message_stop\"}}\n\n"
            finally:
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

    async def handle_non_streaming(
        self,
        req: MessagesRequest,
        provider_config,
        actual_model: str,
        request_id: str,
        start_time: float
    ) -> dict:
        """Handle non-streaming Anthropic-format request.

        Args:
            req: The request object
            provider_config: Provider configuration
            actual_model: The actual model name to use
            request_id: Unique request identifier
            start_time: Request start time

        Returns:
            Anthropic-format response dict
        """
        # Prepare request
        anthropic_request = self._prepare_request(req)
        anthropic_request["model"] = actual_model

        client = AnthropicClient(provider_config)

        try:
            async def make_request():
                async for response in client.messages_async(anthropic_request, stream=False):
                    return response
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

            # Extract provider_message_id and actual provider from response
            if isinstance(response, dict):
                provider_message_id = response.get("id")
                actual_provider = response.get("provider", provider_config.name)
                logger.debug(f"Extracted provider_message_id: {provider_message_id}")
                logger.debug(f"Extracted actual provider: {actual_provider}")
            else:
                provider_message_id = None
                actual_provider = provider_config.name

        except httpx.HTTPStatusError as e:
            error_text = str(e.response.text) if hasattr(e.response, 'text') else ""
            logger.error(f"HTTP error from {provider_config.name}: {e.response.status_code} - {error_text}")
            raise HTTPException(
                status_code=503 if e.response.status_code >= 500 else e.response.status_code,
                detail={
                    "type": "api_error",
                    "message": f"API error from provider '{provider_config.name}': {error_text}",
                    "provider": provider_config.name
                }
            )
        except httpx.RequestError as e:
            logger.error(f"Request error from {provider_config.name}: {e}")
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
            raise HTTPException(
                status_code=500,
                detail={
                    "type": "internal_error",
                    "message": f"Unexpected error: {str(e)}",
                    "provider": provider_config.name
                }
            )

        # Extract usage and log
        input_tokens, output_tokens = self._extract_usage_from_response(response)

        response_time_ms = (time.time() - start_time) * 1000
        await self._log_request(
            request_id=request_id,
            provider_name=provider_config.name,
            model=actual_model,
            request_params=anthropic_request,
            response_data=response,
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
        # Use actual_provider from API response, fallback to provider_config.name
        display_provider = actual_provider or provider_config.name
        provider_width = calculate_display_width(display_provider)
        total_width = 35
        padding_needed = total_width - provider_width - 4
        padding = " " * padding_needed
        end_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        logger.info(
            f"{COLOR_CYAN}[Request {request_id}]{COLOR_RESET}\n"
            f"  {COLOR_GREEN}Non-streaming completed at{COLOR_RESET} {COLOR_YELLOW}{end_timestamp}{COLOR_RESET}\n"
            f"  API Format: anthropic\n"
            f"  Stream: False\n"
            f"  Provider: {provider_config.name}\n"
            f"  {COLOR_GREEN}┌──────── Actual Provider ────────┐{COLOR_RESET}\n"
            f"  {COLOR_GREEN}│ {display_provider}{padding} │{COLOR_RESET}\n"
            f"  {COLOR_GREEN}└─────────────────────────────────┘{COLOR_RESET}\n"
            f"  Model: {actual_model}\n"
            f"  Actual Provider Message ID: {provider_message_id}\n"
            f"  Input Tokens: {input_tokens}\n"
            f"  Output Tokens: {output_tokens}\n"
            f"  Response Time: {response_time_ms:.2f}ms"
        )

        return response
