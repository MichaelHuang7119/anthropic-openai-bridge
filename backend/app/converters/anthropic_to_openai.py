"""Convert Anthropic API format to OpenAI format."""
import logging
import json as json_module
from typing import List, Union, Dict, Any
from ..core import (
    Message, TextContent, ImageContent,
    ToolDefinition, MessagesRequest,
    ToolUseBlock
)

logger = logging.getLogger(__name__)


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
        try:
            return json_module.dumps(content, ensure_ascii=False)
        except:
            return str(content)
    
    return str(content)


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

