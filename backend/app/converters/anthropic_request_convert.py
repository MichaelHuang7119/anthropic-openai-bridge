"""Anthropic to OpenAI request format conversion."""
import logging
import json as json_module
from typing import List, Union, Dict, Any
from ..core import (
    Message, TextContent, ImageContent,
    ToolDefinition, MessagesRequest,
    ToolUseBlock
)

logger = logging.getLogger(__name__)


def format_tool_result(content: Union[str, List, Dict, Any]) -> str:
    """Format tool result content into a string."""
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
                    except (TypeError, ValueError) as e:
                        logger.debug(f"Failed to serialize item to JSON: {e}")
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
        except (TypeError, ValueError) as e:
            logger.debug(f"Failed to serialize content to JSON: {e}")
            return str(content)

    return str(content)


def convert_tool_to_openai(tool: Union[ToolDefinition, Dict[str, Any]]) -> Dict[str, Any]:
    """Convert Anthropic tool definition to OpenAI function format.

    Args:
        tool: The tool definition (Anthropic format)

    Returns:
        OpenAI function format tool definition
    """
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


def to_openai(request: Union[MessagesRequest, Dict[str, Any]]) -> Dict[str, Any]:
    """Convert Anthropic request format to OpenAI format.

    Args:
        request: The Anthropic-format request

    Returns:
        OpenAI-format request dict
    """
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

    # Handle system message
    if system:
        if isinstance(system, str):
            openai_messages.append({"role": "system", "content": system})
        elif isinstance(system, list):
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
            if system_text_parts:
                system_text = " ".join(system_text_parts)
                openai_messages.append({"role": "system", "content": system_text})

    # Convert user/assistant messages
    i = 0
    while i < len(messages):
        msg = messages[i]

        if isinstance(msg, dict):
            msg_obj = Message(**msg)
        else:
            msg_obj = msg

        if msg_obj.role == "assistant":
            openai_msg = _convert_assistant_message(msg_obj)
            openai_messages.append(openai_msg)

            has_tool_calls = (
                openai_msg.get("tool_calls") and
                len(openai_msg.get("tool_calls", [])) > 0
            )

            if has_tool_calls and i + 1 < len(messages):
                next_msg = messages[i + 1]
                if isinstance(next_msg, dict):
                    next_msg_obj = Message(**next_msg)
                else:
                    next_msg_obj = next_msg

                if (next_msg_obj.role == "user" and
                    isinstance(next_msg_obj.content, list) and
                    any(block.get("type") == "tool_result" if isinstance(block, dict)
                        else getattr(block, "type", None) == "tool_result"
                        for block in next_msg_obj.content)):
                    tool_results = _convert_tool_results(next_msg_obj)
                    if tool_results:
                        openai_messages.extend(tool_results)

                    non_tool_content = []
                    for block in next_msg_obj.content:
                        if isinstance(block, dict):
                            block_type = block.get("type")
                        else:
                            block_type = getattr(block, "type", None)

                        if block_type != "tool_result":
                            non_tool_content.append(block)

                    if non_tool_content:
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

                    i += 1

        elif msg_obj.role == "user":
            openai_msg = _convert_user_message(msg_obj)
            openai_messages.append(openai_msg)

            if isinstance(msg_obj.content, list):
                has_tool_results = any(
                    block.get("type") == "tool_result" if isinstance(block, dict)
                    else getattr(block, "type", None) == "tool_result"
                    for block in msg_obj.content
                )

                if has_tool_results:
                    tool_results = _convert_tool_results(msg_obj)
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
            openai_tool = convert_tool_to_openai(tool)
            openai_tools.append(openai_tool)
        openai_request["tools"] = openai_tools

    # Convert tool_choice
    tool_choice = request.get("tool_choice") if isinstance(request, dict) else getattr(request, "tool_choice", None)
    if tool_choice:
        if isinstance(tool_choice, str):
            if tool_choice in ["auto", "none", "any"]:
                openai_request["tool_choice"] = tool_choice
        elif isinstance(tool_choice, dict):
            choice_type = tool_choice.get("type")
            if choice_type == "tool" and "name" in tool_choice:
                openai_request["tool_choice"] = {
                    "type": "function",
                    "function": {"name": tool_choice["name"]}
                }
            elif choice_type in ["auto", "any", "none"]:
                openai_request["tool_choice"] = choice_type
    elif tools:
        openai_request["tool_choice"] = "auto"

    return openai_request


def _convert_user_message(message: Message) -> Dict[str, Any]:
    """Convert Anthropic user message to OpenAI format."""
    role = message.role.value

    if isinstance(message.content, str):
        return {"role": role, "content": message.content}
    else:
        content = []
        for block in message.content:
            block_type = None
            if isinstance(block, dict):
                block_type = block.get("type")
            else:
                block_type = getattr(block, "type", None)

            if block_type == "tool_result":
                continue

            if isinstance(block, (TextContent, dict)):
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        content.append({"type": "text", "text": block.get("text", "")})
                    elif block.get("type") == "image":
                        source = block.get("source", {})
                        if source.get("type") == "base64":
                            media_type = source.get("media_type", "image/jpeg")
                            data = source.get("data", "")
                            content.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:{media_type};base64,{data}"}
                            })
                        elif source.get("type") == "url":
                            content.append({
                                "type": "image_url",
                                "image_url": {"url": source.get("url", "")}
                            })
                else:
                    content.append({"type": "text", "text": block.text})
            elif isinstance(block, ImageContent):
                source = block.source
                if source.type == "base64":
                    media_type = source.media_type or "image/jpeg"
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{source.data}" if source.data else ""}
                    })
                elif source.type == "url":
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": source.url or ""}
                    })
            elif isinstance(block, dict):
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
                            "image_url": {"url": f"data:{media_type};base64,{data}"}
                        })
                    elif source.get("type") == "url":
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": source.get("url", "")}
                        })

        if len(content) == 0:
            return {"role": role, "content": ""}
        elif len(content) == 1 and content[0].get("type") == "text":
            return {"role": role, "content": content[0].get("text", "")}
        else:
            return {"role": role, "content": content}


def _convert_assistant_message(message: Message) -> Dict[str, Any]:
    """Convert Anthropic assistant message to OpenAI format."""
    text_parts = []
    tool_calls = []

    if message.content is None:
        return {"role": "assistant", "content": None}

    if isinstance(message.content, str):
        return {"role": "assistant", "content": message.content}

    for block in message.content:
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
    if text_parts:
        openai_message["content"] = "".join(text_parts)
    else:
        openai_message["content"] = None

    if tool_calls:
        openai_message["tool_calls"] = tool_calls

    return openai_message


def _convert_tool_results(message: Message) -> List[Dict[str, Any]]:
    """Convert Anthropic tool results to OpenAI format."""
    tool_messages = []

    if not isinstance(message.content, list):
        return tool_messages

    for block in message.content:
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
            content_str = format_tool_result(content)
            if is_error:
                content_str = f"Error: {content_str}"

            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_use_id,
                "content": content_str
            })

    return tool_messages
