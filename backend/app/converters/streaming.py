"""Streaming conversion from OpenAI to Anthropic format."""
import uuid
import json as json_module
from typing import AsyncIterator, Dict, Any


import logging
logger = logging.getLogger(__name__)


def _process_reasoning_from_content(
    delta_content: str, reasoning_flag: bool
) -> tuple[str, str | None, bool]:
    """Process reasoning tags in content using state machine approach.

    Args:
        delta_content: The content from this delta
        reasoning_flag: True if we're currently inside a thinking block

    Returns:
        Tuple of (content, reasoning_content, updated_reasoning_flag)
    """
    # Multiple thinking tag formats supported for different AI models
    thinking_tags = [
    ("<think>", "</think>"),
    ("<thinking>", "</thinking>"),
    ("<reason>", "</reason>"),
    ("<reasoning>", "</reasoning>"),
    ("<thought>", "</thought>"),
    ("<Thought>", "</Thought>"),
    ("<|begin_of_thought|>", "<|end_of_thought|>"),
    ("◁think▷", "◁/think▷"),
]

    reasoning_content = ""
    content = ""

    # Find the first matching tag pair
    matched_tags = None
    for REASONING_START_TAG, REASONING_STOP_TAG in thinking_tags:
        reasoning_start_tag_index = delta_content.find(REASONING_START_TAG)
        reasoning_stop_tag_index = delta_content.find(REASONING_STOP_TAG)

        # If we find a valid tag pair, use it
        if reasoning_start_tag_index != -1 or reasoning_stop_tag_index != -1:
            matched_tags = (REASONING_START_TAG, REASONING_STOP_TAG, reasoning_start_tag_index, reasoning_stop_tag_index)
            break

    # If no tags found and not in reasoning mode, return original content
    if not matched_tags and not reasoning_flag:
        return delta_content, None, False

    # If we have matched tags, extract them
    if matched_tags:
        REASONING_START_TAG, REASONING_STOP_TAG, reasoning_start_tag_index, reasoning_stop_tag_index = matched_tags
    else:
        # Use default tags if we're in reasoning mode
        REASONING_START_TAG, REASONING_STOP_TAG = thinking_tags[0]
        reasoning_start_tag_index = -1
        reasoning_stop_tag_index = -1

    # 如果已经在推理模式中，或者发现了开始标签
    if reasoning_flag or reasoning_start_tag_index != -1:
        new_reasoning_flag = True

        # 同时包含开始和结束标签（完整的一次推理块）
        if reasoning_start_tag_index != -1 and reasoning_stop_tag_index != -1:
            # 如果开始标签在结束标签之前
            if reasoning_start_tag_index < reasoning_stop_tag_index:
                # 提取开始标签后的推理内容
                if reasoning_start_tag_index == 0:
                    reasoning_content += delta_content[len(REASONING_START_TAG):reasoning_stop_tag_index]
                else:
                    # 既有开始又有结束，但开始不在最前面
                    content += delta_content[:reasoning_start_tag_index]
                    reasoning_content += delta_content[reasoning_start_tag_index + len(REASONING_START_TAG):reasoning_stop_tag_index]

                # 提取结束标签后的内容（推理块结束）
                remaining = delta_content[reasoning_stop_tag_index + len(REASONING_STOP_TAG):]
                if remaining:
                    content += remaining
                new_reasoning_flag = False  # 推理块结束
            else:
                # 结束标签在开始标签之前（不常见，可能是有问题的输入）
                content += delta_content[:reasoning_stop_tag_index]
                new_reasoning_flag = False
                remaining = delta_content[reasoning_stop_tag_index + len(REASONING_STOP_TAG):]
                if remaining:
                    content += remaining
        # 只找到开始标签（新推理块开始）
        elif reasoning_start_tag_index != -1:
            if reasoning_start_tag_index == 0:
                # 开始标签在最前面，提取标签后的内容
                reasoning_content += delta_content[len(REASONING_START_TAG):]
            else:
                # 开始标签不在最前面，提取前面的正常内容和后面的推理内容
                content += delta_content[:reasoning_start_tag_index]
                reasoning_content += delta_content[reasoning_start_tag_index + len(REASONING_START_TAG):]
        # 只找到结束标签（推理块结束）
        elif reasoning_stop_tag_index != -1:
            # 提取结束标签前的推理内容
            reasoning_part = delta_content[:reasoning_stop_tag_index]
            # 去除末尾的换行
            if reasoning_part.endswith('\n'):
                reasoning_part = reasoning_part[:-1]
            if reasoning_part:
                reasoning_content += reasoning_part

            # 提取结束标签后的内容
            remaining = delta_content[reasoning_stop_tag_index + len(REASONING_STOP_TAG):]
            if remaining:
                content += remaining
            new_reasoning_flag = False  # 推理块结束
        else:
            # 没找到标签，整段都是推理内容
            reasoning_content += delta_content
    else:
        # 没有在推理模式中，也没有找到开始标签，整段都是普通内容
        content = delta_content
        new_reasoning_flag = False

    # 如果没有提取到任何内容，返回 None
    reasoning_content = reasoning_content if reasoning_content else None

    return content, reasoning_content, new_reasoning_flag


async def convert_openai_stream_to_anthropic_async(
    openai_stream: AsyncIterator,
    model: str,
    initial_input_tokens: int = 0
) -> AsyncIterator[Dict[str, Any]]:
    """Convert OpenAI async streaming response to Anthropic format.

    Args:
        openai_stream: Async iterator of OpenAI streaming chunks
        model: Model name
        initial_input_tokens: Initial input token count (calculated from request messages)
    """
    # Validate that we have a valid stream
    if openai_stream is None:
        logger.error(f"openai_stream is None for model {model}")
        raise ValueError("openai_stream cannot be None")

    # Log stream type for debugging
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Starting stream conversion for model {model}, stream type: {type(openai_stream).__name__}")

    message_id = f"msg_{uuid.uuid4().hex[:24]}"
    text_block_index = 0
    tool_block_counter = 0
    current_tool_calls = {}  # Maps OpenAI index -> tool call data
    text_block_started = False
    message_started = False
    final_stop_reason = 'end_turn'  # Default stop reason if none is provided
    last_chunk = None
    finish_reason_seen = False  # Track if we've seen a finish_reason
    # Initialize usage_data with actual input_tokens (per claude-code-proxy pattern)
    # This allows clients to see input token count immediately
    usage_data = {"input_tokens": initial_input_tokens, "output_tokens": 0}

    # Extended thinking support
    thinking_content_blocks = {}  # Maps content block index -> thinking data
    current_thinking_block = None  # Track current thinking block index
    thinking_signature = None  # Store signature for thinking block
    # State tracking for reasoning tag processing
    reasoning_flag = False  # Track if we're inside a thinking block
    provider_extracted = None
    actual_provider = None

    # Send initial SSE events IMMEDIATELY (per claude-code-proxy pattern for better responsiveness)
    # This allows the client to know the request has started processing right away
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

    # Don't start text block immediately - wait for actual content
    # Thinking block will be started first if thinking content is available

    # Send ping event immediately after initial events (per claude-code-proxy pattern)
    # This helps keep the connection alive and provides faster initial response
    yield {
        "type": "ping"
    }

    # Track if we've received any content chunks (not just usage updates)
    has_content_chunks = False
    chunk_count = 0  # Track total chunks received
    chunks_with_choices = 0  # Track chunks that have choices
    chunks_without_choices = 0  # Track chunks without choices

    async for chunk in openai_stream:
        chunk_count += 1
        last_chunk = chunk
        
        # Log chunk info at DEBUG level for troubleshooting
        if logger.isEnabledFor(logging.DEBUG):
            chunk_type = type(chunk).__name__
            has_choices_attr = hasattr(chunk, 'choices')
            is_dict = isinstance(chunk, dict)
            logger.debug(
                f"Received chunk #{chunk_count}: type={chunk_type}, "
                f"has_choices={has_choices_attr}, is_dict={is_dict}"
            )
        
        # Extract usage from chunk if available (when stream_options.include_usage=True)
        # Per OpenAI API: usage appears in the final chunk, which may not have choices
        # Try multiple methods to extract usage (OpenAI SDK objects can vary)
        chunk_usage = None
        
        # Method 1: Direct attribute access (OpenAI SDK object)
        if hasattr(chunk, 'usage') and chunk.usage:
            chunk_usage = chunk.usage
        
        # Method 2: Convert to dict and check (like claude-code-proxy)
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
        
        # Extract thinking signature from chunk if available
        # Some providers send signature in the final chunk
        thinking_signature = None
        if isinstance(chunk, dict):
            thinking_signature = chunk.get("signature") or chunk.get("thinking_signature")
        elif hasattr(chunk, 'signature'):
            thinking_signature = getattr(chunk, 'signature', None)
        elif hasattr(chunk, 'thinking_signature'):
            thinking_signature = getattr(chunk, 'thinking_signature', None)
        
        # Store signature if we have a thinking block and received a signature
        if thinking_signature and current_thinking_block is not None:
            thinking_content_blocks[current_thinking_block]["signature"] = thinking_signature
        
        # Extract usage data if found and send real-time updates (per claude-code-proxy pattern)
        # When OpenAI API provides usage data (usually in final chunk with stream_options.include_usage=True),
        # update both input_tokens (more accurate than estimation) and output_tokens
        usage_updated = False
        if chunk_usage:
            if isinstance(chunk_usage, dict):
                # Safely extract values, handling None cases
                prompt_tokens = chunk_usage.get('prompt_tokens')
                completion_tokens = chunk_usage.get('completion_tokens')
                new_usage = {
                    "input_tokens": prompt_tokens if prompt_tokens is not None else usage_data["input_tokens"],
                    "output_tokens": completion_tokens if completion_tokens is not None else usage_data["output_tokens"]
                }
            elif hasattr(chunk_usage, 'prompt_tokens'):
                # Safely extract values, handling None cases
                prompt_tokens = getattr(chunk_usage, 'prompt_tokens', None)
                completion_tokens = getattr(chunk_usage, 'completion_tokens', None)
                new_usage = {
                    "input_tokens": prompt_tokens if prompt_tokens is not None else usage_data["input_tokens"],
                    "output_tokens": completion_tokens if completion_tokens is not None else usage_data["output_tokens"]
                }
            else:
                new_usage = None
            
            # Update usage_data if we got new data (especially output_tokens which increases during streaming)
            if new_usage:
                # Ensure values are integers (handle None cases)
                new_output_tokens = new_usage.get("output_tokens", 0) or 0
                new_input_tokens = new_usage.get("input_tokens", 0) or 0
                
                # Always update output_tokens if it's greater (it increases during streaming)
                if isinstance(new_output_tokens, int) and new_output_tokens > usage_data["output_tokens"]:
                    usage_data["output_tokens"] = new_output_tokens
                    usage_updated = True
                
                # Update input_tokens if API provided a value (more accurate than estimation)
                if isinstance(new_input_tokens, int) and new_input_tokens > 0 and new_input_tokens != usage_data["input_tokens"]:
                    usage_data["input_tokens"] = new_input_tokens
                    usage_updated = True
        
        # Send real-time usage update if it changed (per claude-code-proxy pattern)
        # This allows clients to see token consumption in real-time
        # Send update whenever output_tokens increases (real-time progress)
        # BUT: Don't send message_delta during content streaming to avoid event ordering issues
        # Only send usage updates in the final message_delta
        
        # Handle OpenAI SDK response objects
        # Support multiple chunk formats: SDK objects, dicts, etc.
        # Extract provider info from the first chunk only
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
            logger.debug(f"Extracted provider from chunk: {actual_provider}")

            # Send message_metadata with actual_provider information immediately after extraction
            yield {
                "type": "message_metadata",
                "actual_provider": actual_provider,
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
        
        # If chunk has usage but no choices, check for special content types
        # This is expected for the final usage chunk, but also for thinking content
        if not choices:
            chunks_without_choices += 1
            
            # Check for thinking content in chunks without choices (aiping format)
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
                
                # Initialize thinking block if not already started
                if current_thinking_block is None:
                    current_thinking_block = text_block_index + 1
                    thinking_content_blocks[current_thinking_block] = {
                        "thinking": "",
                        "signature": None
                    }
                    
                    # Send content_block_start for thinking
                    yield {
                        "type": "content_block_start",
                        "index": current_thinking_block,
                        "content_block": {
                            "type": "thinking",
                            "thinking": ""
                        }
                    }
                
                # Accumulate and send thinking content
                if isinstance(thinking_content, str):
                    thinking_content_blocks[current_thinking_block]["thinking"] += thinking_content
                    
                    # Send thinking_delta event
                    yield {
                        "type": "content_block_delta",
                        "index": current_thinking_block,
                        "delta": {
                            "type": "thinking_delta",
                            "thinking": thinking_content
                        }
                    }
                continue
            
            # Check for signature in chunks without choices
            signature = None
            if hasattr(chunk, 'signature'):
                signature = chunk.signature
            elif isinstance(chunk, dict):
                signature = chunk.get('signature') or chunk.get('thinking_signature')
            
            if signature and current_thinking_block is not None:
                thinking_content_blocks[current_thinking_block]["signature"] = signature
                continue
            
            # Check for direct content in chunk (non-standard format)
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
            
            # Log at DEBUG level why we're skipping this chunk
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"Skipping chunk #{chunk_count}: no choices found. "
                    f"Chunk keys: {list(chunk.keys()) if isinstance(chunk, dict) else 'N/A'}"
                )
            continue
        
        chunks_with_choices += 1
        
        if not choices or len(choices) == 0:
            # Empty choices list - might be the last chunk
            continue
        
        choice = choices[0]
        # Handle delta as object (OpenAI SDK) or dict
        delta = None
        if isinstance(choice, dict):
            delta = choice.get('delta', {})
        elif hasattr(choice, 'delta'):
            delta = getattr(choice, 'delta', None)
        
        if delta is None:
            delta = {}
        
        # Get finish_reason - this indicates the stream is ending
        # Some APIs send finish_reason in the last chunk with content
        # Others send it in a separate final chunk
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
        
        # Helper to get delta attribute safely
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
        
        # Handle text delta (message_start and content_block_start already sent above)
        content = get_delta_attr('content')
        # Also check if content is directly in choice (some API formats)
        if not content:
            content = get_choice_attr('content') or get_choice_attr('text')
        
        # Handle thinking content (extended thinking feature)
        # Check multiple possible attribute names for thinking content
        thinking_content = None
        
        # First check if thinking is directly in the chunk (some providers send it at top level)
        # This is the most common format for thinking content
        if hasattr(chunk, 'thinking'):
            thinking_content = chunk.thinking
            if thinking_content and logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Found thinking content in chunk attribute: {str(thinking_content)[:50]}...")
        if not thinking_content and isinstance(chunk, dict):
            for attr in ['thinking', 'reasoning', 'reasoning_content', 'thought']:
                if attr in chunk:
                    thinking_content = chunk[attr]
                    if thinking_content and logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Found thinking content in chunk dict: {str(thinking_content)[:50]}...")
                    break
        
        # Then check delta attributes (OpenAI SDK format)
        if not thinking_content:
            for attr in ['thinking', 'reasoning', 'reasoning_content', 'thought']:
                thinking_content = get_delta_attr(attr)
                if thinking_content:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Found thinking content in delta attr '{attr}': {str(thinking_content)[:50]}...")
                    break
            if not thinking_content and logger.isEnabledFor(logging.DEBUG):
                # Log delta keys for debugging
                if isinstance(delta, dict):
                    logger.debug(f"No thinking content in delta, delta keys: {list(delta.keys())}")
                else:
                    logger.debug(f"No thinking content in delta, delta type: {type(delta).__name__}")

        # Check for reasoning_details format (array of text fragments)
        if not thinking_content:
            reasoning_details = get_delta_attr('reasoning_details')
            if reasoning_details:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Found reasoning_details: {reasoning_details}")
                if isinstance(reasoning_details, list):
                    reasoning_parts = []
                    for detail in reasoning_details:
                        if isinstance(detail, dict) and detail.get('text'):
                            reasoning_parts.append(detail.get('text'))
                        elif hasattr(detail, 'text') and detail.text:
                            reasoning_parts.append(str(detail.text))
                    if reasoning_parts:
                        thinking_content = ''.join(reasoning_parts)
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"Extracted thinking from reasoning_details: {str(thinking_content)[:50]}...")

        # Finally check choice attributes (some API formats)
        if not thinking_content:
            for attr in ['thinking', 'reasoning', 'reasoning_content', 'thought']:
                thinking_content = get_choice_attr(attr)
                if thinking_content:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Found thinking content in choice: {str(thinking_content)[:50]}...")
                    break

        # If no thinking_content found yet, check if content contains reasoning tags using unified state machine
        if not thinking_content and content:
            content, thinking_content, reasoning_flag = _process_reasoning_from_content(
                content, reasoning_flag
            )
            
        # Process thinking content if available
        if thinking_content:
            has_content_chunks = True
            logger.debug(f"Processing thinking content: {str(thinking_content)[:50]}... (text_block_index={text_block_index}, current_thinking_block={current_thinking_block})")

            # Initialize thinking block if not already started
            if current_thinking_block is None:
                current_thinking_block = text_block_index + 1
                thinking_content_blocks[current_thinking_block] = {
                    "thinking": "",
                    "signature": None
                }
                logger.debug(f"Initialized thinking block at index {current_thinking_block}")

                # Send content_block_start for thinking
                yield {
                    "type": "content_block_start",
                    "index": current_thinking_block,
                    "content_block": {
                        "type": "thinking",
                        "thinking": ""
                    }
                }
                logger.debug(f"Sent content_block_start for thinking block {current_thinking_block}")

            # Accumulate thinking content
            if isinstance(thinking_content, str):
                thinking_content_blocks[current_thinking_block]["thinking"] += thinking_content
                logger.debug(f"Accumulated thinking content, total length: {len(thinking_content_blocks[current_thinking_block]['thinking'])}")

                # Send thinking_delta event
                event = {
                    "type": "content_block_delta",
                    "index": current_thinking_block,
                    "delta": {
                        "type": "thinking_delta",
                        "thinking": thinking_content
                    }
                }
                yield event
                logger.debug(f"Sent thinking_delta event for chunk '{thinking_content[:30]}...'")
        
        # Handle regular text content
        if content is not None and content != "":
            has_content_chunks = True
            logger.debug(f"Processing text content: '{content[:50]}...'")

            # Start text block if not already started
            if not text_block_started:
                # If we have a thinking block, text block comes after it
                if current_thinking_block is not None:
                    text_block_index = current_thinking_block + 1
                else:
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
        
        # Handle tool calls with improved incremental processing
        tool_calls = get_delta_attr('tool_calls')
        if tool_calls:
            for tc_delta in tool_calls:
                # Helper to get tool call delta attribute safely
                def get_tc_attr(attr, default=None):
                    if hasattr(tc_delta, attr):
                        return getattr(tc_delta, attr)
                    elif isinstance(tc_delta, dict):
                        return tc_delta.get(attr, default)
                    return default
                
                tc_index = get_tc_attr('index', 0)
                
                # Initialize tool call tracking if not exists
                if tc_index not in current_tool_calls:
                    current_tool_calls[tc_index] = {
                        "id": None,
                        "name": None,
                        "args_buffer": [],  # Use list instead of string for better performance
                        "args_str": "",     # Cache the joined string
                        "json_sent": False,
                        "claude_index": None,
                        "started": False
                    }
                
                tool_call = current_tool_calls[tc_index]
                
                # Update tool call ID if provided
                tool_call_id = get_tc_attr('id')
                if tool_call_id:
                    tool_call["id"] = tool_call_id
                
                # Update function name
                func = get_tc_attr('function')
                if func:
                    # Handle func as object or dict
                    if hasattr(func, 'name'):
                        func_name = getattr(func, 'name', None)
                    elif isinstance(func, dict):
                        func_name = func.get('name')
                    else:
                        func_name = None
                    
                    if func_name:
                        tool_call["name"] = func_name
                
                # Start content block when we have both id and name
                if tool_call["id"] and tool_call["name"] and not tool_call["started"]:
                    has_content_chunks = True
                    tool_block_counter += 1
                    claude_index = text_block_index + tool_block_counter
                    tool_call["claude_index"] = claude_index
                    tool_call["started"] = True
                    
                    # Determine content block type - check if this is a server tool
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
                
                # Handle function arguments - send when we have valid JSON
                if func and tool_call["started"]:
                    # Get arguments from func object or dict
                    if hasattr(func, 'arguments'):
                        arguments = getattr(func, 'arguments') or ''
                    elif isinstance(func, dict):
                        arguments = func.get('arguments') or ''
                    else:
                        arguments = ''
                    
                    if arguments:
                        # Use list append for O(1) complexity instead of string concatenation O(n)
                        tool_call["args_buffer"].append(arguments)

                        # Optimize: Only try to parse JSON periodically or when buffer grows
                        # This reduces CPU overhead for incomplete JSON
                        buffer_len = sum(len(s) for s in tool_call["args_buffer"])
                        
                        # Only attempt parsing if:
                        # 1. We haven't sent JSON yet AND
                        # 2. Buffer is reasonably sized (avoid parsing tiny fragments)
                        # 3. Or buffer ends with '}' (likely complete)
                        should_try_parse = (
                            not tool_call["json_sent"] and 
                            buffer_len > 10 and  # Minimum size to avoid parsing tiny fragments
                            (buffer_len % 50 == 0 or arguments.rstrip().endswith('}'))  # Periodic or likely complete
                        )
                        
                        if should_try_parse:
                            # Only join the string when we need to parse
                            buffer_str = ''.join(tool_call["args_buffer"])
                            try:
                                json_module.loads(buffer_str)
                                # If parsing succeeds and we haven't sent this JSON yet
                                yield {
                                    "type": "content_block_delta",
                                    "index": tool_call["claude_index"],
                                    "delta": {
                                        "type": "input_json_delta",
                                        "partial_json": buffer_str
                                    }
                                }
                                tool_call["json_sent"] = True
                                # Cache the joined string to avoid re-joining
                                tool_call["args_str"] = buffer_str
                            except json_module.JSONDecodeError:
                                # JSON is incomplete, continue accumulating
                                pass
        
        # Handle finish reason - break loop when we get finish_reason
        # Note: Some APIs send finish_reason in the same chunk as the last content
        # Others send it in a separate final chunk. We handle both cases.
        if finish_reason:
            # Map OpenAI finish_reason to Anthropic stop_reason
            stop_reason = None
            if finish_reason == 'stop':
                stop_reason = 'end_turn'
            elif finish_reason in ['tool_calls', 'function_call']:
                stop_reason = 'tool_use'
            elif finish_reason == 'length':
                stop_reason = 'max_tokens'
            else:
                stop_reason = 'end_turn'
            
            # Store for final events
            final_stop_reason = stop_reason
            finish_reason_seen = True
            # Don't break immediately - process any remaining content in this chunk first
            # The loop will naturally end when the stream ends
            # This handles cases where finish_reason comes with the last content chunk
            # Some APIs send finish_reason in the same chunk as the last content, then end the stream
    
    # usage_data is already initialized and updated during the loop
    # No need to extract from last_chunk since we update it in real-time
    
    # If we didn't see a finish_reason, the stream ended naturally
    # This is normal for some APIs that don't send finish_reason or [DONE] markers
    if not finish_reason_seen:
        logger.debug(
            f"OpenAI stream ended naturally without finish_reason. "
            f"Model: {model}, Using default stop_reason: {final_stop_reason}"
        )
    
    # Log warning if we didn't receive any content chunks (only usage updates)
    # This might indicate the API returned an empty response
    if not has_content_chunks:
        # Log more details for debugging
        logger.warning(
            f"OpenAI stream conversion completed without any content chunks. "
            f"Model: {model}, Only received usage updates or empty stream. "
            f"Total chunks received: {chunk_count}, "
            f"Chunks with choices: {chunks_with_choices}, "
            f"Chunks without choices: {chunks_without_choices}, "
            f"Last chunk type: {type(last_chunk).__name__ if last_chunk else 'None'}, "
            f"Has choices attr: {hasattr(last_chunk, 'choices') if last_chunk else False}, "
            f"Is dict: {isinstance(last_chunk, dict) if last_chunk else False}"
        )
        
        # If no chunks were received at all, this is a more serious issue
        if chunk_count == 0:
            logger.error(
                f"No chunks received from OpenAI stream for model {model}. "
                f"This indicates the stream was empty or the connection was closed immediately."
            )
        
        # If we have last_chunk, log its structure for debugging
        if last_chunk and logger.isEnabledFor(logging.DEBUG):
            try:
                if hasattr(last_chunk, 'model_dump'):
                    chunk_dict = last_chunk.model_dump()
                elif isinstance(last_chunk, dict):
                    chunk_dict = last_chunk
                else:
                    chunk_dict = {"type": type(last_chunk).__name__, "repr": str(last_chunk)[:200]}
                logger.debug(f"Last chunk structure: {chunk_dict}")
            except Exception as e:
                logger.debug(f"Could not inspect last chunk: {e}")
        
        # If we received chunks but none had content, log sample chunks
        if chunk_count > 0 and logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Received {chunk_count} chunks but none contained content. "
                f"This might indicate the API returned only usage/metadata chunks."
            )

    # Send signature_delta for thinking block if we have one
    if current_thinking_block is not None:
        thinking_data = thinking_content_blocks.get(current_thinking_block, {})
        signature = thinking_data.get("signature")
        
        if signature:
            # Send signature_delta event before content_block_stop
            yield {
                "type": "content_block_delta",
                "index": current_thinking_block,
                "delta": {
                    "type": "signature_delta",
                    "signature": signature
                }
            }
    
    # Send final SSE events in correct order
    # First, stop all content blocks (text and tools)
    
    # Stop text block
    yield {
        "type": "content_block_stop",
        "index": text_block_index
    }
    
    # Stop thinking block if exists
    if current_thinking_block is not None:
        yield {
            "type": "content_block_stop",
            "index": current_thinking_block
        }
    
    # Stop all tool blocks
    for tool_data in current_tool_calls.values():
        if tool_data.get("started") and tool_data.get("claude_index") is not None:
            # Ensure JSON is sent if we have complete JSON but haven't sent it
            if tool_data["args_buffer"] and not tool_data["json_sent"]:
                # Use cached string if available, otherwise join
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
                    # Even if JSON is invalid, send what we have (partial JSON is allowed)
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
    
    # Send message_delta with stop_reason and usage (AFTER all content_block_stop events)
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



