"""Test assistant messages with tool_use blocks conversion."""
import pytest
from app.converter import convert_anthropic_assistant_message_to_openai
from app.models import Message, MessageRole, ToolUseBlock


def test_assistant_message_with_tool_use():
    """Test converting assistant message with tool_use blocks."""
    # Create assistant message with tool_use
    assistant_msg = Message(
        role=MessageRole.ASSISTANT,
        content=[
            {
                "type": "tool_use",
                "id": "tool_123",
                "name": "read_file",
                "input": {"path": "/test.txt"}
            }
        ]
    )
    
    result = convert_anthropic_assistant_message_to_openai(assistant_msg)
    
    assert result["role"] == "assistant"
    assert result["content"] is None
    assert "tool_calls" in result
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["id"] == "tool_123"
    assert result["tool_calls"][0]["type"] == "function"
    assert result["tool_calls"][0]["function"]["name"] == "read_file"


def test_assistant_message_with_text_and_tool_use():
    """Test converting assistant message with both text and tool_use."""
    assistant_msg = Message(
        role=MessageRole.ASSISTANT,
        content=[
            {"type": "text", "text": "I'll read the file."},
            {
                "type": "tool_use",
                "id": "tool_456",
                "name": "read_file",
                "input": {"path": "/test.txt"}
            }
        ]
    )
    
    result = convert_anthropic_assistant_message_to_openai(assistant_msg)
    
    assert result["role"] == "assistant"
    assert result["content"] == "I'll read the file."
    assert "tool_calls" in result
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["id"] == "tool_456"


def test_assistant_message_with_multiple_tool_use():
    """Test converting assistant message with multiple tool_use blocks."""
    assistant_msg = Message(
        role=MessageRole.ASSISTANT,
        content=[
            {
                "type": "tool_use",
                "id": "tool_1",
                "name": "read_file",
                "input": {"path": "/file1.txt"}
            },
            {
                "type": "tool_use",
                "id": "tool_2",
                "name": "write_file",
                "input": {"path": "/file2.txt", "content": "test"}
            }
        ]
    )
    
    result = convert_anthropic_assistant_message_to_openai(assistant_msg)
    
    assert result["role"] == "assistant"
    assert result["content"] is None
    assert len(result["tool_calls"]) == 2
    assert result["tool_calls"][0]["id"] == "tool_1"
    assert result["tool_calls"][1]["id"] == "tool_2"



