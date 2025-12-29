"""OpenAI to Anthropic response conversion."""
import uuid
import json as json_module
import logging
from typing import AsyncIterator, Dict, Any

from ..utils.token_extractor import extract_tokens_from_usage

logger = logging.getLogger(__name__)


def _handle_thinking_from_streaming_content(delta_content: str, reasoning_flag: bool) -> tuple:
    """Process thinking tags from content using unified state machine.

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
    """
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

    reasoning_content = ""
    content = ""

    matched_tags = None
    for REASONING_START_TAG, REASONING_STOP_TAG in thinking_tags:
        reasoning_start_tag_index = delta_content.find(REASONING_START_TAG)
        reasoning_stop_tag_index = delta_content.find(REASONING_STOP_TAG)

        if reasoning_start_tag_index != -1 or reasoning_stop_tag_index != -1:
            matched_tags = (REASONING_START_TAG, REASONING_STOP_TAG, reasoning_start_tag_index, reasoning_stop_tag_index)
            break

    if not matched_tags and not reasoning_flag:
        return delta_content, None, False

    if matched_tags:
        REASONING_START_TAG, REASONING_STOP_TAG, reasoning_start_tag_index, reasoning_stop_tag_index = matched_tags
    else:
        REASONING_START_TAG, REASONING_STOP_TAG = thinking_tags[0]
        reasoning_start_tag_index = -1
        reasoning_stop_tag_index = -1

    if reasoning_flag or reasoning_start_tag_index != -1:
        new_reasoning_flag = True

        if reasoning_start_tag_index != -1 and reasoning_stop_tag_index != -1:
            if reasoning_start_tag_index < reasoning_stop_tag_index:
                # 内容在开始标签之前 -> 这部分应该是content，不是thinking
                content += delta_content[:reasoning_start_tag_index]
                # thinking内容在标签之间
                reasoning_content += delta_content[reasoning_start_tag_index + len(REASONING_START_TAG):reasoning_stop_tag_index]

                remaining = delta_content[reasoning_stop_tag_index + len(REASONING_STOP_TAG):]
                if remaining:
                    content += remaining
                new_reasoning_flag = False
            else:
                # 结束标签在开始标签之前 -> 结束标签之前的内容应该是content
                content += delta_content[:reasoning_stop_tag_index]
                new_reasoning_flag = False
                remaining = delta_content[reasoning_stop_tag_index + len(REASONING_STOP_TAG):]
                if remaining:
                    content += remaining
        elif reasoning_start_tag_index != -1:
            if reasoning_start_tag_index == 0:
                reasoning_content += delta_content[len(REASONING_START_TAG):]
            else:
                content += delta_content[:reasoning_start_tag_index]
                reasoning_content += delta_content[reasoning_start_tag_index + len(REASONING_START_TAG):]
        elif reasoning_stop_tag_index != -1:
            reasoning_part = delta_content[:reasoning_stop_tag_index]
            if reasoning_part.endswith('\n'):
                reasoning_part = reasoning_part[:-1]
            if reasoning_part:
                reasoning_content += reasoning_part

            remaining = delta_content[reasoning_stop_tag_index + len(REASONING_STOP_TAG):]
            if remaining:
                content += remaining
            new_reasoning_flag = False
        else:
            reasoning_content += delta_content
    else:
        content = delta_content
        new_reasoning_flag = False

    reasoning_content = reasoning_content if reasoning_content else None

    return content, reasoning_content, new_reasoning_flag


def to_anthropic(
    openai_response: Dict[str, Any],
    model: str
) -> Dict[str, Any]:
    """Convert OpenAI response format to Anthropic format (non-streaming).

    Args:
        openai_response: The OpenAI response dict
        model: The model name

    Returns:
        Anthropic-format response dict
    """
    choices = openai_response.get('choices')

    if choices is None:
        error = openai_response.get('error', {})
        if error:
            error_msg = error.get('message', 'Unknown error')
            error_type = error.get('type', 'api_error')
            raise ValueError(f"OpenAI API error ({error_type}): {error_msg}")
        raise ValueError("Invalid OpenAI response: choices is None.")

    if not isinstance(choices, list) or len(choices) == 0:
        error = openai_response.get('error', {})
        if error:
            error_msg = error.get('message', 'Unknown error')
            error_type = error.get('type', 'api_error')
            raise ValueError(f"OpenAI API error ({error_type}): {error_msg}")
        raise ValueError("Invalid OpenAI response: no choices in response.")

    choice = choices[0]

    # Handle both dict and Pydantic object - convert to dict
    if not isinstance(choice, dict):
        if hasattr(choice, 'model_dump'):
            choice = choice.model_dump()
        elif hasattr(choice, 'dict'):
            choice = choice.dict()
        elif hasattr(choice, '__dict__'):
            choice_dict = {
                'message': {},
                'finish_reason': getattr(choice, 'finish_reason', None)
            }
            if hasattr(choice, 'message'):
                msg = choice.message
                if hasattr(msg, 'model_dump'):
                    choice_dict['message'] = msg.model_dump()
                elif hasattr(msg, 'dict'):
                    choice_dict['message'] = msg.dict()
                elif hasattr(msg, '__dict__'):
                    choice_dict['message'] = {
                        'role': getattr(msg, 'role', 'assistant'),
                        'content': getattr(msg, 'content', None) or "",
                        'tool_calls': []
                    }
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tc in msg.tool_calls:
                            tc_dict = {
                                'id': getattr(tc, 'id', ''),
                                'type': getattr(tc, 'type', 'function'),
                                'function': {}
                            }
                            if hasattr(tc, 'function'):
                                func = tc.function
                                tc_dict['function'] = {
                                    'name': getattr(func, 'name', ''),
                                    'arguments': getattr(func, 'arguments', '{}')
                                }
                            choice_dict['message']['tool_calls'].append(tc_dict)
                else:
                    choice_dict['message'] = {}
            choice = choice_dict
        else:
            original_choice = choice
            choice = {
                'message': {},
                'finish_reason': getattr(original_choice, 'finish_reason', 'stop')
            }
            if hasattr(original_choice, 'message'):
                msg = original_choice.message
                choice['message'] = {
                    'role': getattr(msg, 'role', 'assistant'),
                    'content': getattr(msg, 'content', None) or "",
                    'tool_calls': []
                }

    message = choice.get('message', {})

    # Build content blocks
    content_blocks = []

    if 'content' in message and message['content']:
        content_blocks.append({
            "type": "text",
            "text": message['content'],
            "citations": None
        })

    tool_calls = message.get('tool_calls')
    if not tool_calls:
        tool_calls = []
    for tool_call in tool_calls:
        if tool_call.get('type') == 'function':
            func = tool_call.get('function', {})
            try:
                input_data = json_module.loads(func.get('arguments', '{}'))
            except:
                input_data = {}

            content_blocks.append({
                "type": "tool_use",
                "id": tool_call.get('id', ''),
                "name": func.get('name', ''),
                "input": input_data
            })

    # Map finish_reason to stop_reason
    finish_reason = choice.get('finish_reason', 'stop')
    stop_reason = None
    if finish_reason == 'stop':
        stop_reason = 'end_turn'
    elif finish_reason == 'tool_calls':
        stop_reason = 'tool_use'
    elif finish_reason == 'length':
        stop_reason = 'max_tokens'

    usage = openai_response.get('usage')

    # 使用统一的 token 提取工具，支持多种 API 格式
    input_tokens, output_tokens = extract_tokens_from_usage(usage)

    # 如果还是None，使用0作为默认值
    input_tokens = input_tokens if input_tokens is not None else 0
    output_tokens = output_tokens if output_tokens is not None else 0

    message_id = openai_response.get('id')
    provider = openai_response.get("provider")

    response = {
        "id": message_id,
        "provider": provider,
        "type": "message",
        "role": "assistant",
        "content": content_blocks if content_blocks else [{"type": "text", "text": ""}],
        "model": model,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        },
        "context_management": None,
        "container": None
    }

    return response


async def to_anthropic_async(
    openai_stream: AsyncIterator,
    model: str,
    initial_input_tokens: int = 0
) -> AsyncIterator[Dict[str, Any]]:
    """Convert OpenAI streaming response to Anthropic streaming format.

    Args:
        openai_stream: Async iterator of OpenAI streaming chunks
        model: Model name
        initial_input_tokens: Initial input token count

    Yields:
        Anthropic-format streaming chunks
    """
    if openai_stream is None:
        logger.error(f"openai_stream is None for model {model}")
        raise ValueError("openai_stream cannot be None")

    message_id = f"msg_{uuid.uuid4().hex[:24]}"
    text_block_index = 0
    tool_block_counter = 0
    current_tool_calls = {}
    text_block_started = False
    final_stop_reason = 'end_turn'
    finish_reason_seen = False
    usage_data = {"input_tokens": initial_input_tokens, "output_tokens": 0}

    thinking_content_blocks = {}
    current_thinking_block = None
    thinking_signature = None
    thinking_finished = False
    thinking_stop_sent = False
    reasoning_flag = False
    previous_reasoning_flag = False
    provider_extracted = None
    actual_provider = None

    # Send initial SSE events
    yield {
        "type": "message_start",
        "message": {
            "id": message_id,
            "type": "message",
            "role": "assistant",
            "content": [],
            "model": model,
            "stop_reason": None,
            "stop_sequence": None,
            "usage": usage_data
        }
    }

    yield {"type": "ping"}

    has_content_chunks = False
    chunk_count = 0
    chunks_with_choices = 0
    chunks_without_choices = 0

    async for chunk in openai_stream:
        logger.debug(f"OpenAI streaming: {chunk}")
        chunk_count += 1

        # Extract message_id from OpenAI chunk if available
        actual_message_id = None
        if isinstance(chunk, dict):
            actual_message_id = chunk.get("id")
        elif hasattr(chunk, 'id'):
            actual_message_id = getattr(chunk, 'id')

        # Extract usage from chunk
        chunk_usage = None
        if hasattr(chunk, 'usage') and chunk.usage:
            chunk_usage = chunk.usage
        if not chunk_usage:
            try:
                if hasattr(chunk, 'model_dump'):
                    chunk_dict = chunk.model_dump()
                    chunk_usage = chunk_dict.get("usage")
                elif hasattr(chunk, 'dict'):
                    chunk_dict = chunk.dict()
                    chunk_usage = chunk_dict.get("usage")
                elif isinstance(chunk, dict):
                    chunk_usage = chunk.get("usage")
            except Exception:
                pass

        # Extract thinking signature
        thinking_signature = None
        if isinstance(chunk, dict):
            thinking_signature = chunk.get("signature") or chunk.get("thinking_signature")
        elif hasattr(chunk, 'signature'):
            thinking_signature = getattr(chunk, 'signature', None)
        elif hasattr(chunk, 'thinking_signature'):
            thinking_signature = getattr(chunk, 'thinking_signature', None)

        if thinking_signature and current_thinking_block is not None:
            thinking_content_blocks[current_thinking_block]["signature"] = thinking_signature

        # Update usage data using unified extractor
        if chunk_usage:
            # 使用统一的 token 提取工具
            new_input, new_output = extract_tokens_from_usage(chunk_usage)

            # 只在有新值时更新
            if new_input is not None:
                if isinstance(new_input, int) and new_input > 0 and new_input != usage_data["input_tokens"]:
                    usage_data["input_tokens"] = new_input
            if new_output is not None:
                if isinstance(new_output, int) and new_output > usage_data["output_tokens"]:
                    usage_data["output_tokens"] = new_output

        # Extract provider info
        if not provider_extracted:
            if hasattr(chunk, "provider"):
                actual_provider = chunk.provider
            elif isinstance(chunk, dict):
                actual_provider = chunk.get("provider")
                if not actual_provider and "provider" in chunk:
                    actual_provider = chunk["provider"]
            elif hasattr(chunk, "model_dump"):
                try:
                    chunk_dict = chunk.model_dump()
                    actual_provider = chunk_dict.get("provider")
                except:
                    pass

            provider_extracted = True
            yield {
                "type": "message_metadata",
                "actual_provider": actual_provider,
                "actual_message_id": actual_message_id,
            }

        choices = None
        if hasattr(chunk, 'choices'):
            choices = chunk.choices
        elif isinstance(chunk, dict):
            choices = chunk.get('choices')
        elif hasattr(chunk, 'model_dump'):
            try:
                chunk_dict = chunk.model_dump()
                choices = chunk_dict.get('choices')
            except:
                pass

        if not choices:
            chunks_without_choices += 1

            # Check for thinking content
            thinking_content = None
            if hasattr(chunk, 'thinking'):
                thinking_content = chunk.thinking
            elif isinstance(chunk, dict):
                for attr in ['thinking', 'reasoning', 'reasoning_content', 'thought']:
                    if attr in chunk:
                        thinking_content = chunk[attr]
                        break

            if thinking_content:
                has_content_chunks = True
                if current_thinking_block is None:
                    current_thinking_block = text_block_index + 1
                    thinking_content_blocks[current_thinking_block] = {
                        "thinking": "",
                        "signature": None
                    }
                    yield {
                        "type": "content_block_start",
                        "index": current_thinking_block,
                        "content_block": {
                            "type": "thinking",
                            "thinking": ""
                        }
                    }

                if isinstance(thinking_content, str):
                    thinking_content_blocks[current_thinking_block]["thinking"] += thinking_content
                    yield {
                        "type": "content_block_delta",
                        "index": current_thinking_block,
                        "delta": {
                            "type": "thinking_delta",
                            "thinking": thinking_content
                        }
                    }
                continue

            # Check for signature
            signature = None
            if hasattr(chunk, 'signature'):
                signature = chunk.signature
            elif isinstance(chunk, dict):
                signature = chunk.get('signature') or chunk.get('thinking_signature')

            if signature and current_thinking_block is not None:
                thinking_content_blocks[current_thinking_block]["signature"] = signature
                continue

            # Check for direct content
            if isinstance(chunk, dict):
                direct_content = chunk.get('content') or chunk.get('text')
                if direct_content:
                    has_content_chunks = True
                    yield {
                        "type": "content_block_delta",
                        "index": text_block_index,
                        "delta": {
                            "type": "text_delta",
                            "text": direct_content
                        }
                    }
                    continue
            continue

        chunks_with_choices += 1

        if not choices or len(choices) == 0:
            continue

        choice = choices[0]
        delta = None
        if isinstance(choice, dict):
            delta = choice.get('delta', {})
        elif hasattr(choice, 'delta'):
            delta = getattr(choice, 'delta', None)

        if delta is None:
            delta = {}

        finish_reason = None
        if isinstance(choice, dict):
            finish_reason = choice.get('finish_reason')
        elif hasattr(choice, 'finish_reason'):
            finish_reason = getattr(choice, 'finish_reason', None)
        elif hasattr(choice, 'model_dump'):
            try:
                choice_dict = choice.model_dump()
                finish_reason = choice_dict.get('finish_reason')
            except:
                pass

        def get_delta_attr(attr, default=None):
            if isinstance(delta, dict):
                return delta.get(attr, default)
            elif hasattr(delta, attr):
                return getattr(delta, attr)
            return default

        def get_choice_attr(attr, default=None):
            if isinstance(choice, dict):
                return choice.get(attr, default)
            elif hasattr(choice, attr):
                return getattr(choice, attr)
            return default

        content = get_delta_attr('content')
        if not content:
            content = get_choice_attr('content') or get_choice_attr('text')

        # Handle thinking content
        thinking_content = None
        if hasattr(chunk, 'thinking'):
            thinking_content = chunk.thinking
        if not thinking_content and isinstance(chunk, dict):
            for attr in ['thinking', 'reasoning', 'reasoning_content', 'thought']:
                if attr in chunk:
                    thinking_content = chunk[attr]
                    break

        if not thinking_content:
            for attr in ['thinking', 'reasoning', 'reasoning_content', 'thought']:
                thinking_content = get_delta_attr(attr)
                if thinking_content:
                    break

        if not thinking_content:
            reasoning_details = get_delta_attr('reasoning_details')
            if reasoning_details and isinstance(reasoning_details, list):
                reasoning_parts = []
                for detail in reasoning_details:
                    if isinstance(detail, dict) and detail.get('text'):
                        reasoning_parts.append(detail.get('text'))
                    elif hasattr(detail, 'text') and detail.text:
                        reasoning_parts.append(str(detail.text))
                if reasoning_parts:
                    thinking_content = ''.join(reasoning_parts)

        if not thinking_content:
            for attr in ['thinking', 'reasoning', 'reasoning_content', 'thought']:
                thinking_content = get_choice_attr(attr)
                if thinking_content:
                    break

        if not thinking_content and content:
            # 保存旧的 reasoning_flag 状态
            previous_reasoning_flag = reasoning_flag
            content, thinking_content, reasoning_flag = _handle_thinking_from_streaming_content(content, reasoning_flag)

        # 如果 reasoning_flag 从 True 变为 False，说明遇到了结束标签
        if previous_reasoning_flag is True and reasoning_flag is False:
            thinking_finished = True

        if thinking_content:
            has_content_chunks = True
            # 只有在没有遇到 reasoning 结束标签的情况下才重置 thinking_finished
            if not (previous_reasoning_flag is True and reasoning_flag is False):
                thinking_finished = False
            if current_thinking_block is None:
                current_thinking_block = text_block_index
                thinking_content_blocks[current_thinking_block] = {
                    "thinking": "",
                    "signature": None
                }
                yield {
                    "type": "content_block_start",
                    "index": current_thinking_block,
                    "content_block": {
                        "type": "thinking",
                        "thinking": ""
                    }
                }

            if isinstance(thinking_content, str):
                thinking_content_blocks[current_thinking_block]["thinking"] += thinking_content
                yield {
                    "type": "content_block_delta",
                    "index": current_thinking_block,
                    "delta": {
                        "type": "thinking_delta",
                        "thinking": thinking_content
                    }
                }
        else:
            if current_thinking_block is not None and not thinking_finished:
                thinking_finished = True

        # Handle text content
        if content is not None and content != "" and (current_thinking_block is None or thinking_finished):
            has_content_chunks = True

            # If we have a thinking block that hasn't been stopped yet, stop it now
            if current_thinking_block is not None and not thinking_stop_sent:
                # Send signature_delta before stopping the thinking block
                thinking_data = thinking_content_blocks.get(current_thinking_block, {})
                signature = thinking_data.get("signature")

                # If no signature provided, generate a pseudo-signature based on thinking content
                if not signature:
                    import hashlib
                    thinking_content = thinking_data.get("thinking", "")
                    if thinking_content:
                        signature_hash = hashlib.sha256(thinking_content.encode()).hexdigest()
                        signature = signature_hash[:64]

                # Always send signature_delta (use empty string if no signature available)
                if signature is None:
                    signature = ""
                yield {
                    "type": "content_block_delta",
                    "index": current_thinking_block,
                    "delta": {
                        "type": "signature_delta",
                        "signature": signature
                    }
                }

                # Now send the thinking block stop
                yield {
                    "type": "content_block_stop",
                    "index": current_thinking_block
                }
                thinking_stop_sent = True
                text_block_index = current_thinking_block + 1

                # Start the text block
                yield {
                    "type": "content_block_start",
                    "index": text_block_index,
                    "content_block": {
                        "type": "text",
                        "text": ""
                    }
                }
                text_block_started = True
            elif not text_block_started:
                text_block_index = 0
                yield {
                    "type": "content_block_start",
                    "index": text_block_index,
                    "content_block": {
                        "type": "text",
                        "text": ""
                    }
                }
                text_block_started = True

            yield {
                "type": "content_block_delta",
                "index": text_block_index,
                "delta": {
                    "type": "text_delta",
                    "text": content
                }
            }

        # Handle tool calls
        tool_calls = get_delta_attr('tool_calls')
        if tool_calls:
            for tc_delta in tool_calls:
                def get_tc_attr(attr, default=None):
                    if hasattr(tc_delta, attr):
                        return getattr(tc_delta, attr)
                    elif isinstance(tc_delta, dict):
                        return tc_delta.get(attr, default)
                    return default

                tc_index = get_tc_attr('index', 0)

                if tc_index not in current_tool_calls:
                    current_tool_calls[tc_index] = {
                        "id": None,
                        "name": None,
                        "args_buffer": [],
                        "args_str": "",
                        "json_sent": False,
                        "claude_index": None,
                        "started": False
                    }

                tool_call = current_tool_calls[tc_index]

                tool_call_id = get_tc_attr('id')
                if tool_call_id:
                    tool_call["id"] = tool_call_id

                func = get_tc_attr('function')
                if func:
                    if hasattr(func, 'name'):
                        func_name = getattr(func, 'name', None)
                    elif isinstance(func, dict):
                        func_name = func.get('name')
                    else:
                        func_name = None

                    if func_name:
                        tool_call["name"] = func_name

                tools_ready = (
                    (current_thinking_block is None or thinking_finished) and
                    (not text_block_started or thinking_finished)
                )

                if tool_call["id"] and tool_call["name"] and not tool_call["started"] and tools_ready:
                    has_content_chunks = True
                    tool_block_counter += 1
                    claude_index = max(text_block_index + 1, current_thinking_block + 1 if current_thinking_block else 1) + tool_block_counter - 1
                    tool_call["claude_index"] = claude_index
                    tool_call["started"] = True

                    tool_name = tool_call["name"]
                    is_server_tool = tool_name in ["web_search", "web_search_20250305"]

                    yield {
                        "type": "content_block_start",
                        "index": claude_index,
                        "content_block": {
                            "type": "server_tool_use" if is_server_tool else "tool_use",
                            "id": tool_call["id"],
                            "name": tool_call["name"],
                            "input": {}
                        }
                    }

                if func and tool_call["started"]:
                    if hasattr(func, 'arguments'):
                        arguments = getattr(func, 'arguments') or ''
                    elif isinstance(func, dict):
                        arguments = func.get('arguments') or ''
                    else:
                        arguments = ''

                    if arguments:
                        tool_call["args_buffer"].append(arguments)
                        buffer_len = sum(len(s) for s in tool_call["args_buffer"])

                        should_try_parse = (
                            not tool_call["json_sent"] and
                            buffer_len > 10 and
                            (buffer_len % 50 == 0 or arguments.rstrip().endswith('}'))
                        )

                        if should_try_parse:
                            buffer_str = ''.join(tool_call["args_buffer"])
                            try:
                                json_module.loads(buffer_str)
                                yield {
                                    "type": "content_block_delta",
                                    "index": tool_call["claude_index"],
                                    "delta": {
                                        "type": "input_json_delta",
                                        "partial_json": buffer_str
                                    }
                                }
                                tool_call["json_sent"] = True
                                tool_call["args_str"] = buffer_str
                            except json_module.JSONDecodeError:
                                pass

        if finish_reason:
            stop_reason = None
            if finish_reason == 'stop':
                stop_reason = 'end_turn'
            elif finish_reason in ['tool_calls', 'function_call']:
                stop_reason = 'tool_use'
            elif finish_reason == 'length':
                stop_reason = 'max_tokens'
            else:
                stop_reason = 'end_turn'

            final_stop_reason = stop_reason
            finish_reason_seen = True

    if not finish_reason_seen:
        logger.debug(f"OpenAI stream ended naturally without finish_reason. Model: {model}")

    if not has_content_chunks:
        logger.warning(
            f"OpenAI stream conversion completed without any content chunks. "
            f"Model: {model}, Total chunks: {chunk_count}"
        )

    # Stop thinking block if not already stopped (handles case where there's only thinking, no text)
    if current_thinking_block is not None and not thinking_stop_sent:
        # Send signature_delta before stopping thinking block
        thinking_data = thinking_content_blocks.get(current_thinking_block, {})
        signature = thinking_data.get("signature")

        # If no signature provided, generate a pseudo-signature based on thinking content
        if not signature:
            import hashlib
            thinking_content = thinking_data.get("thinking", "")
            signature_hash = hashlib.sha256(thinking_content.encode()).hexdigest()
            signature = signature_hash[:64]

        if signature:
            yield {
                "type": "content_block_delta",
                "index": current_thinking_block,
                "delta": {
                    "type": "signature_delta",
                    "signature": signature
                }
            }

        yield {
            "type": "content_block_stop",
            "index": current_thinking_block
        }

    # Stop text block
    if text_block_started:
        yield {
            "type": "content_block_stop",
            "index": text_block_index
        }

    # Stop all tool blocks
    for tool_data in current_tool_calls.values():
        if tool_data.get("started") and tool_data.get("claude_index") is not None:
            if tool_data["args_buffer"] and not tool_data["json_sent"]:
                buffer_str = tool_data.get("args_str") or ''.join(tool_data["args_buffer"])
                try:
                    json_module.loads(buffer_str)
                    yield {
                        "type": "content_block_delta",
                        "index": tool_data["claude_index"],
                        "delta": {
                            "type": "input_json_delta",
                            "partial_json": buffer_str
                        }
                    }
                except:
                    yield {
                        "type": "content_block_delta",
                        "index": tool_data["claude_index"],
                        "delta": {
                            "type": "input_json_delta",
                            "partial_json": buffer_str
                        }
                    }

            yield {
                "type": "content_block_stop",
                "index": tool_data["claude_index"]
            }

    # Send message_delta
    yield {
        "type": "message_delta",
        "delta": {
            "stop_reason": final_stop_reason,
            "stop_sequence": None
        },
        "usage": usage_data
    }

    # Send message_stop
    yield {"type": "message_stop"}
