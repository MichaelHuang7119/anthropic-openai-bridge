"""Test tool use response format compliance with Anthropic spec."""
import os
import sys
import pytest

# Add parent directory to Python path for CI/CD environments
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backend.app.converters import convert_openai_response_to_anthropic


def test_tool_use_response_format():
    """Test that tool_use blocks match Anthropic format."""
    openai_response = {
        "id": "chatcmpl-123",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_abc123",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"location": "San Francisco"}'
                            }
                        }
                    ]
                },
                "finish_reason": "tool_calls"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 0
        }
    }
    
    anthropic_response = convert_openai_response_to_anthropic(
        openai_response,
        "haiku",
        stream=False
    )
    
    # Verify response structure
    assert anthropic_response["type"] == "message"
    assert anthropic_response["role"] == "assistant"
    assert anthropic_response["stop_reason"] == "tool_use"
    
    # Verify tool_use block format
    content_blocks = anthropic_response["content"]
    assert len(content_blocks) == 1
    tool_block = content_blocks[0]
    
    assert tool_block["type"] == "tool_use"
    assert "id" in tool_block
    assert tool_block["name"] == "get_weather"
    assert tool_block["input"] == {"location": "San Francisco"}


def test_text_with_citations():
    """Test that text blocks include citations field."""
    openai_response = {
        "id": "chatcmpl-123",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hello, world!"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5
        }
    }
    
    anthropic_response = convert_openai_response_to_anthropic(
        openai_response,
        "haiku",
        stream=False
    )
    
    content_blocks = anthropic_response["content"]
    assert len(content_blocks) == 1
    text_block = content_blocks[0]
    
    assert text_block["type"] == "text"
    assert text_block["text"] == "Hello, world!"
    assert "citations" in text_block  # Should include citations field per spec
    assert text_block["citations"] is None


def test_mixed_content_text_and_tools():
    """Test response with both text and tool calls."""
    openai_response = {
        "id": "chatcmpl-123",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "I'll check the weather for you.",
                    "tool_calls": [
                        {
                            "id": "call_xyz789",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"location": "NYC"}'
                            }
                        }
                    ]
                },
                "finish_reason": "tool_calls"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5
        }
    }
    
    anthropic_response = convert_openai_response_to_anthropic(
        openai_response,
        "haiku",
        stream=False
    )
    
    assert anthropic_response["stop_reason"] == "tool_use"
    content_blocks = anthropic_response["content"]
    
    # Should have both text and tool_use blocks
    assert len(content_blocks) >= 2
    assert content_blocks[0]["type"] == "text"
    assert content_blocks[0]["citations"] is None
    assert content_blocks[1]["type"] == "tool_use"



