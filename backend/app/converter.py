"""Convert between Anthropic and OpenAI API formats."""
import logging
from typing import List, Union, Dict, Any, Optional, AsyncIterator, Iterator
from .models import (
    Message, TextContent, ImageContent, ContentBlock,
    ToolDefinition, MessagesRequest,
    TextBlock, ToolUseBlock
)

logger = logging.getLogger(__name__)


def convert_anthropic_message_to_openai(message: Message) -> Dict[str, Any]:
    """Convert Anthropic message format to OpenAI format."""
    role = message.role.value
    
    # Assistant messages need special handling for tool_use blocks
    if role == "assistant":
        return convert_anthropic_assistant_message_to_openai(message)
    
    # Handle user messages - filter out tool_result blocks (they're handled separately)
    if isinstance(message.content, str):
        # For simple text content, use string format (more compatible with various providers)
        # Only use array format when there are multiple content types (e.g., text + images)
        return {"role": role, "content": message.content}
    else:
        content = []
        for block in message.content:
            # Skip tool_result blocks - they're handled separately
            block_type = None
            if isinstance(block, dict):
                block_type = block.get("type")
            else:
                block_type = getattr(block, "type", None)
            
            if block_type == "tool_result":
                # Skip tool_result - handled separately
                continue
                
            if isinstance(block, (TextContent, dict)):
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        content.append({"type": "text", "text": block.get("text", "")})
                    elif block.get("type") == "image":
                        # Convert image content
                        source = block.get("source", {})
                        if source.get("type") == "base64":
                            # OpenAI uses data URI format
                            media_type = source.get("media_type", "image/jpeg")
                            data = source.get("data", "")
                            content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{data}"
                                }
                            })
                        elif source.get("type") == "url":
                            content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": source.get("url", "")
                                }
                            })
                else:
                    # TextContent object
                    content.append({"type": "text", "text": block.text})
            elif isinstance(block, ImageContent):
                # Handle ImageContent
                source = block.source
                if source.type == "base64":
                    media_type = source.media_type or "image/jpeg"
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{source.data}" if source.data else ""
                        }
                    })
                elif source.type == "url":
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": source.url or ""}
                    })
            elif isinstance(block, dict):
                # Handle dict-based content blocks (excluding tool_result)
                block_type = block.get("type")
                if block_type == "text":
                    content.append({"type": "text", "text": block.get("text", "")})
                elif block_type == "image":
                    source = block.get("source", {})
                    if source.get("type") == "base64":
                        media_type = source.get("media_type", "image/jpeg")
                        data = source.get("data", "")
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{data}"
                            }
                        })
                    elif source.get("type") == "url":
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": source.url or ""}
                        })
        
        # Return content - use string format if only one text block, otherwise use array format
        if len(content) == 0:
            # Empty content if all blocks were tool_result
            return {"role": role, "content": ""}
        elif len(content) == 1 and content[0].get("type") == "text":
            # Single text block - use string format for better compatibility
            return {"role": role, "content": content[0].get("text", "")}
        else:
            # Multiple blocks or non-text content (e.g., images) - use array format
            return {"role": role, "content": content}


def convert_anthropic_assistant_message_to_openai(message: Message) -> Dict[str, Any]:
    """Convert Anthropic assistant message to OpenAI format, handling tool_use blocks."""
    import json as json_module
    
    text_parts = []
    tool_calls = []
    
    if message.content is None:
        return {"role": "assistant", "content": None}
    
    if isinstance(message.content, str):
        return {"role": "assistant", "content": message.content}
    
    for block in message.content:
        # Handle both dict and object formats
        if isinstance(block, dict):
            block_type = block.get("type")
            if block_type == "text":
                text_parts.append(block.get("text", ""))
            elif block_type == "tool_use":
                tool_calls.append({
                    "id": block.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": block.get("name", ""),
                        "arguments": json_module.dumps(block.get("input", {}), ensure_ascii=False)
                    }
                })
        else:
            # Handle object format - prefer direct attribute access for performance
            # Only fall back to model_dump if necessary (it's slower)
            block_type = getattr(block, "type", None)
            block_dict = {}
            if not block_type and hasattr(block, 'model_dump'):
                block_dict = block.model_dump()
                block_type = block_dict.get("type")
            
            if block_type == "text" or isinstance(block, TextContent):
                text = block_dict.get("text") or getattr(block, "text", "")
                if text:
                    text_parts.append(text)
            elif block_type == "tool_use" or isinstance(block, ToolUseBlock):
                tool_id = block_dict.get("id") or getattr(block, "id", "")
                tool_name = block_dict.get("name") or getattr(block, "name", "")
                tool_input = block_dict.get("input") or getattr(block, "input", {})
                
                tool_calls.append({
                    "id": tool_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json_module.dumps(tool_input, ensure_ascii=False)
                    }
                })
    
    openai_message = {"role": "assistant"}
    
    # Set content
    if text_parts:
        openai_message["content"] = "".join(text_parts)
    else:
        openai_message["content"] = None
    
    # Set tool calls
    if tool_calls:
        openai_message["tool_calls"] = tool_calls
    
    return openai_message


def convert_anthropic_tool_to_openai(tool: Union[ToolDefinition, Dict[str, Any]]) -> Dict[str, Any]:
    """Convert Anthropic tool definition to OpenAI function format."""
    if isinstance(tool, dict):
        return {
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {})
            }
        }
    else:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema
            }
        }


def parse_tool_result_content(content: Union[str, List, Dict, Any]) -> str:
    """Parse and normalize tool result content into a string format."""
    if content is None:
        return "No content provided"
    
    if isinstance(content, str):
        return content
    
    if isinstance(content, list):
        result_parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    result_parts.append(item.get("text", ""))
                elif "text" in item:
                    result_parts.append(str(item.get("text", "")))
                else:
                    import json as json_module
                    try:
                        result_parts.append(json_module.dumps(item, ensure_ascii=False))
                    except:
                        result_parts.append(str(item))
            elif isinstance(item, str):
                result_parts.append(item)
            else:
                result_parts.append(str(item))
        return "\n".join(result_parts).strip()
    
    if isinstance(content, dict):
        if content.get("type") == "text":
            return content.get("text", "")
        import json as json_module
        try:
            return json_module.dumps(content, ensure_ascii=False)
        except:
            return str(content)
    
    return str(content)


def convert_anthropic_tool_results_to_openai(message: Message) -> List[Dict[str, Any]]:
    """Convert Anthropic tool results to OpenAI format."""
    tool_messages = []
    
    if not isinstance(message.content, list):
        return tool_messages
    
    for block in message.content:
        # Handle both dict and object formats
        if isinstance(block, dict):
            block_type = block.get("type")
            tool_use_id = block.get("tool_use_id")
            content = block.get("content")
            is_error = block.get("is_error", False)
        else:
            block_type = getattr(block, "type", None)
            tool_use_id = getattr(block, "tool_use_id", None)
            content = getattr(block, "content", None)
            is_error = getattr(block, "is_error", False)
        
        if block_type == "tool_result" and tool_use_id:
            content_str = parse_tool_result_content(content)
            if is_error:
                # Format error as string
                content_str = f"Error: {content_str}"
            
            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_use_id,
                "content": content_str
            })
    
    return tool_messages


def convert_anthropic_request_to_openai(request: Union[MessagesRequest, Dict[str, Any]]) -> Dict[str, Any]:
    """Convert Anthropic request format to OpenAI format."""
    if isinstance(request, dict):
        messages = request.get("messages", [])
        tools = request.get("tools")
        model = request.get("model")
        max_tokens = request.get("max_tokens")
        temperature = request.get("temperature")
        stream = request.get("stream", False)
        system = request.get("system")
    else:
        messages = request.messages
        tools = request.tools
        model = request.model
        max_tokens = request.max_tokens
        temperature = request.temperature
        stream = request.stream
        system = request.system
    
    # Convert messages
    openai_messages = []
    
    # Handle system message (if present)
    if system:
        if isinstance(system, str):
            # Simple string system message
            openai_messages.append({"role": "system", "content": system})
        elif isinstance(system, list):
            # System message as content blocks array
            system_text_parts = []
            for block in system:
                if isinstance(block, dict):
                    block_type = block.get("type")
                    if block_type == "text":
                        text = block.get("text", "")
                        if text:
                            system_text_parts.append(text)
                elif isinstance(block, TextContent):
                    if block.text:
                        system_text_parts.append(block.text)
                # Note: we ignore other block types (e.g., ephemeral) as they're not needed for OpenAI format
            # Combine all text blocks into a single system message
            if system_text_parts:
                system_text = " ".join(system_text_parts)
                openai_messages.append({"role": "system", "content": system_text})
    
    # Convert user/assistant messages, handling tool results
    # Critical: If assistant message has tool_calls, ALL tool_call_ids must have corresponding tool messages
    i = 0
    while i < len(messages):
        msg = messages[i]
        
        if isinstance(msg, dict):
            msg_obj = Message(**msg)
        else:
            msg_obj = msg
        
        if msg_obj.role == "assistant":
            # Convert assistant message (may contain tool_use blocks)
            openai_msg = convert_anthropic_assistant_message_to_openai(msg_obj)
            openai_messages.append(openai_msg)
            
            # Check if assistant message has tool_calls
            has_tool_calls = (
                openai_msg.get("tool_calls") and 
                len(openai_msg.get("tool_calls", [])) > 0
            )
            
            # If assistant has tool_calls, check next message for tool_results
            if has_tool_calls and i + 1 < len(messages):
                next_msg = messages[i + 1]
                if isinstance(next_msg, dict):
                    next_msg_obj = Message(**next_msg)
                else:
                    next_msg_obj = next_msg
                
                # Check if next message is user message with tool_result blocks
                if (next_msg_obj.role == "user" and 
                    isinstance(next_msg_obj.content, list) and
                    any(block.get("type") == "tool_result" if isinstance(block, dict) 
                        else getattr(block, "type", None) == "tool_result" 
                        for block in next_msg_obj.content)):
                    # Extract all tool_results from this user message
                    tool_results = convert_anthropic_tool_results_to_openai(next_msg_obj)
                    if tool_results:
                        openai_messages.extend(tool_results)
                    
                    # Get tool_call_ids from assistant message
                    tool_call_ids = {tc.get("id") for tc in openai_msg.get("tool_calls", [])}
                    tool_result_ids = {tr.get("tool_call_id") for tr in tool_results}
                    
                    # Verify all tool_call_ids have corresponding tool results
                    missing_ids = tool_call_ids - tool_result_ids
                    if missing_ids:
                        logger.warning(
                            f"Assistant message has tool_calls but missing tool results for IDs: {missing_ids}. "
                            f"Will attempt to process remaining user message content."
                        )
                    
                    # Also process non-tool_result content from the user message
                    # (e.g., text blocks that come after tool_results)
                    non_tool_content = []
                    for block in next_msg_obj.content:
                        if isinstance(block, dict):
                            block_type = block.get("type")
                        else:
                            block_type = getattr(block, "type", None)
                        
                        if block_type != "tool_result":
                            non_tool_content.append(block)
                    
                    if non_tool_content:
                        # Create a user message with remaining content
                        user_msg_content = []
                        for block in non_tool_content:
                            if isinstance(block, dict):
                                user_msg_content.append(block)
                            else:
                                user_msg_content.append(block.model_dump() if hasattr(block, "model_dump") else block)
                        
                        if user_msg_content:
                            openai_messages.append({
                                "role": "user",
                                "content": user_msg_content
                            })
                    
                    # Skip the processed user message
                    i += 1
        
        elif msg_obj.role == "user":
            # Regular user message processing
            # Note: User messages following assistant messages with tool_calls and tool_results
            # are already processed above when handling the assistant message
            openai_msg = convert_anthropic_message_to_openai(msg_obj)
            openai_messages.append(openai_msg)
            
            # Also extract tool_results if present in the user message
            if isinstance(msg_obj.content, list):
                has_tool_results = any(
                    block.get("type") == "tool_result" if isinstance(block, dict) 
                    else getattr(block, "type", None) == "tool_result" 
                    for block in msg_obj.content
                )
                
                if has_tool_results:
                    tool_results = convert_anthropic_tool_results_to_openai(msg_obj)
                    if tool_results:
                        openai_messages.extend(tool_results)
        
        i += 1
    
    # Build OpenAI request
    openai_request: Dict[str, Any] = {
        "model": model,
        "messages": openai_messages,
        "max_tokens": max_tokens,
        "stream": stream
    }
    
    if temperature is not None:
        openai_request["temperature"] = temperature
    
    # Convert tools
    if tools:
        openai_tools = []
        for tool in tools:
            openai_tool = convert_anthropic_tool_to_openai(tool)
            openai_tools.append(openai_tool)
        openai_request["tools"] = openai_tools
    
    # Convert tool_choice
    tool_choice = request.get("tool_choice") if isinstance(request, dict) else getattr(request, "tool_choice", None)
    if tool_choice:
        if isinstance(tool_choice, str):
            # Simple string: "auto", "none", "any"
            if tool_choice in ["auto", "none", "any"]:
                openai_request["tool_choice"] = tool_choice
        elif isinstance(tool_choice, dict):
            # Object format: {"type": "tool", "name": "tool_name"} or {"type": "auto"/"any"/"none"}
            choice_type = tool_choice.get("type")
            if choice_type == "tool" and "name" in tool_choice:
                openai_request["tool_choice"] = {
                    "type": "function",
                    "function": {"name": tool_choice["name"]}
                }
            elif choice_type in ["auto", "any", "none"]:
                openai_request["tool_choice"] = choice_type
    elif tools:
        # Default to "auto" if tools are provided but tool_choice is not specified
        openai_request["tool_choice"] = "auto"
    
    return openai_request


def convert_openai_response_to_anthropic(
    openai_response: Dict[str, Any],
    model: str,
    stream: bool = False
) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
    """Convert OpenAI response format to Anthropic format."""
    if stream:
        # Handle streaming response
        def stream_generator():
            for chunk in openai_response:
                chunk_data = chunk.choices[0] if hasattr(chunk, 'choices') else chunk
                delta = getattr(chunk_data, 'delta', {}) if hasattr(chunk_data, 'delta') else chunk_data.get('delta', {})
                
                # Handle content delta
                if 'content' in delta and delta['content']:
                    yield {
                        "type": "content_block_delta",
                        "index": 0,
                        "delta": {
                            "type": "text_delta",
                            "text": delta['content']
                        }
                    }
                
                # Handle tool calls
                if 'tool_calls' in delta and delta.get('tool_calls'):
                    for tool_call in delta['tool_calls']:
                        if tool_call.get('type') == 'function':
                            func = tool_call.get('function', {})
                            if tool_call.get('index') == 0:
                                yield {
                                    "type": "content_block_start",
                                    "index": 0,
                                    "content_block": {
                                        "type": "tool_use",
                                        "id": tool_call.get('id', ''),
                                        "name": func.get('name', ''),
                                        "input": {}
                                    }
                                }
                            if 'arguments' in func:
                                yield {
                                    "type": "content_block_delta",
                                    "index": 0,
                                    "delta": {
                                        "type": "input_json_delta",
                                        "partial_json": func['arguments']
                                    }
                                }
                
                # Handle finish
                if getattr(chunk_data, 'finish_reason', None) or chunk_data.get('finish_reason'):
                    finish_reason = getattr(chunk_data, 'finish_reason', None) or chunk_data.get('finish_reason')
                    if finish_reason == 'stop':
                        yield {
                            "type": "message_stop"
                        }
                    elif finish_reason == 'tool_calls':
                        yield {
                            "type": "content_block_stop",
                            "index": 0
                        }
                
                # Handle usage
                if hasattr(chunk, 'usage') and chunk.usage:
                    yield {
                        "type": "message_delta",
                        "delta": {
                            "stop_reason": getattr(chunk_data, 'finish_reason', None) or chunk_data.get('finish_reason')
                        },
                        "usage": {
                            "input_tokens": getattr(chunk.usage, 'prompt_tokens', 0),
                            "output_tokens": getattr(chunk.usage, 'completion_tokens', 0)
                        }
                    }
        
        return stream_generator()
    else:
        # Handle non-streaming response
        choices = openai_response.get('choices', [])
        if not choices:
            raise ValueError("Invalid OpenAI response: no choices")
        
        choice = choices[0]
        message = choice.get('message', {})
        
        # Build content blocks
        content_blocks = []
        text_content = ""
        
        # Handle text content
        if 'content' in message and message['content']:
            text_content = message['content']
            content_blocks.append({
                "type": "text",
                "text": text_content,
                "citations": None  # Per Anthropic spec, text blocks include citations field
            })
        
        # Handle tool calls
        tool_calls = message.get('tool_calls')
        if not tool_calls:  # Handles None, [], and empty iterables
            tool_calls = []
        for tool_call in tool_calls:
            if tool_call.get('type') == 'function':
                func = tool_call.get('function', {})
                try:
                    import json
                    input_data = json.loads(func.get('arguments', '{}'))
                except:
                    input_data = {}
                
                content_blocks.append({
                    "type": "tool_use",
                    "id": tool_call.get('id', ''),
                    "name": func.get('name', ''),
                    "input": input_data
                })
        
        # Determine stop reason - map OpenAI finish_reason to Anthropic stop_reason
        finish_reason = choice.get('finish_reason', 'stop')
        stop_reason = None
        if finish_reason == 'stop':
            stop_reason = 'end_turn'
        elif finish_reason == 'tool_calls':
            stop_reason = 'tool_use'  # When model invokes tools
        elif finish_reason == 'length':
            stop_reason = 'max_tokens'
        # Note: Anthropic also supports 'stop_sequence', 'pause_turn', 'refusal', 
        # 'model_context_window_exceeded' but OpenAI doesn't have direct equivalents
        
        # Build Anthropic response - per official spec at https://docs.claude.com/en/api/messages
        usage = openai_response.get('usage', {})
        
        # Generate a unique message ID if not present (per Anthropic format)
        import uuid
        message_id = openai_response.get('id', '')
        if not message_id or not message_id.startswith('msg_'):
            # Anthropic uses format: msg_<24 hex chars>
            message_id = f"msg_{uuid.uuid4().hex[:24]}"
        
        response = {
            "id": message_id,
            "type": "message",  # Always "message" per spec
            "role": "assistant",  # Always "assistant" per spec
            "content": content_blocks if content_blocks else [{"type": "text", "text": ""}],  # Ensure at least one block
            "model": model,
            "stop_reason": stop_reason,  # Required field, can be: end_turn, max_tokens, stop_sequence, tool_use, pause_turn, refusal, model_context_window_exceeded
            "stop_sequence": None,  # Required field, null if no custom stop sequence
            "usage": {
                "input_tokens": usage.get('prompt_tokens', 0),
                "output_tokens": usage.get('completion_tokens', 0)
            },
            # Optional fields per spec (set to None if not available)
            "context_management": None,
            "container": None
        }
        
        return response


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
    import uuid
    import json as json_module
    
    message_id = f"msg_{uuid.uuid4().hex[:24]}"
    text_block_index = 0
    tool_block_counter = 0
    current_tool_calls = {}  # Maps OpenAI index -> tool call data
    text_block_started = False
    message_started = False
    final_stop_reason = 'end_turn'
    last_chunk = None
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
            continue
        
        if not chunk.choices:
            continue
        
        choice = chunk.choices[0]
        # Handle delta as object (OpenAI SDK) or dict
        delta = getattr(choice, 'delta', None)
        if delta is None:
            delta = {}
        finish_reason = getattr(choice, 'finish_reason', None)
        
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
            break
    
    # usage_data is already initialized and updated during the loop
    # No need to extract from last_chunk since we update it in real-time
    
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
                    json_module.loads(tool_data["args_buffer"])
                    yield {
                        "type": "content_block_delta",
                        "index": tool_data["claude_index"],
                        "delta": {
                            "type": "input_json_delta",
                            "partial_json": tool_data["args_buffer"]
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

