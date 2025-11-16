"""Streaming conversion from OpenAI to Anthropic format."""
import uuid
import json as json_module
from typing import AsyncIterator, Dict, Any


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
    last_sent_usage = {"input_tokens": initial_input_tokens, "output_tokens": 0}  # Track last sent usage for real-time updates
    
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
    message_started = True
    
    # Always start text block immediately after message_start (per claude-code-proxy)
    yield {
        "type": "content_block_start",
        "index": text_block_index,
        "content_block": {
            "type": "text",
            "text": ""
        }
    }
    text_block_started = True
    
    # Send ping event immediately after initial events (per claude-code-proxy pattern)
    # This helps keep the connection alive and provides faster initial response
    yield {
        "type": "ping"
    }
    
    # Track if we've received any content chunks (not just usage updates)
    has_content_chunks = False
    async for chunk in openai_stream:
        last_chunk = chunk
        
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
        if usage_updated and (usage_data["output_tokens"] > last_sent_usage["output_tokens"] or 
                             usage_data["input_tokens"] != last_sent_usage["input_tokens"]):
            yield {
                "type": "message_delta",
                "delta": {
                    "stop_reason": None,
                    "stop_sequence": None
                },
                "usage": usage_data
            }
            last_sent_usage = usage_data.copy()
        
        # Handle OpenAI SDK response objects
        if not hasattr(chunk, 'choices'):
            # If chunk has usage but no choices, continue to next chunk
            # This is expected for the final usage chunk
            # However, if this is the last chunk and we haven't seen finish_reason,
            # the stream might have ended naturally
            continue
        
        if not chunk.choices:
            # Empty choices list - might be the last chunk
            # Check if we have finish_reason from previous chunks
            continue
        
        choice = chunk.choices[0]
        # Handle delta as object (OpenAI SDK) or dict
        delta = getattr(choice, 'delta', None)
        if delta is None:
            delta = {}
        
        # Get finish_reason - this indicates the stream is ending
        # Some APIs send finish_reason in the last chunk with content
        # Others send it in a separate final chunk
        finish_reason = getattr(choice, 'finish_reason', None)
        
        # Also check if finish_reason is in the choice dict format
        if not finish_reason and isinstance(choice, dict):
            finish_reason = choice.get('finish_reason')
        elif not finish_reason and hasattr(choice, 'model_dump'):
            try:
                choice_dict = choice.model_dump()
                finish_reason = choice_dict.get('finish_reason')
            except:
                pass
        
        # Helper to get delta attribute safely
        def get_delta_attr(attr, default=None):
            if hasattr(delta, attr):
                return getattr(delta, attr)
            elif isinstance(delta, dict):
                return delta.get(attr, default)
            return default
        
        # Handle text delta (message_start and content_block_start already sent above)
        content = get_delta_attr('content')
        if content:
            has_content_chunks = True
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
                    
                    yield {
                        "type": "content_block_start",
                        "index": claude_index,
                        "content_block": {
                            "type": "tool_use",
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

                        # Try to parse complete JSON and send delta only when valid
                        # Only join the string when we need to parse or send
                        buffer_str = ''.join(tool_call["args_buffer"])
                        try:
                            json_module.loads(buffer_str)
                            # If parsing succeeds and we haven't sent this JSON yet
                            if not tool_call["json_sent"]:
                                yield {
                                    "type": "content_block_delta",
                                    "index": tool_call["claude_index"],
                                    "delta": {
                                        "type": "input_json_delta",
                                        "partial_json": buffer_str
                                    }
                                }
                                tool_call["json_sent"] = True
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
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(
            f"OpenAI stream ended naturally without finish_reason. "
            f"Model: {model}, Using default stop_reason: {final_stop_reason}"
        )
    
    # Log warning if we didn't receive any content chunks (only usage updates)
    # This might indicate the API returned an empty response
    if not has_content_chunks:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"OpenAI stream conversion completed without any content chunks. "
            f"Model: {model}, Only received usage updates or empty stream."
        )
    
    # Send final SSE events
    # Per claude-code-proxy: Always stop text block (even if empty)
    yield {
        "type": "content_block_stop",
        "index": text_block_index
    }
    
    # Stop all tool blocks
    for tool_data in current_tool_calls.values():
        if tool_data.get("started") and tool_data.get("claude_index") is not None:
            # Ensure JSON is sent if we have complete JSON but haven't sent it
            if tool_data["args_buffer"] and not tool_data["json_sent"]:
                try:
                    json_module.loads(''.join(tool_data["args_buffer"]))
                    yield {
                        "type": "content_block_delta",
                        "index": tool_data["claude_index"],
                        "delta": {
                            "type": "input_json_delta",
                            "partial_json": ''.join(tool_data["args_buffer"])
                        }
                    }
                except:
                    pass
            
            yield {
                "type": "content_block_stop",
                "index": tool_data["claude_index"]
            }
    
    # Send message_delta with stop_reason and usage
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



