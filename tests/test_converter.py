"""Tests for converter functions."""
import os
import sys
import pytest

# Add parent directory to Python path for CI/CD environments
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backend.app.converters import (
    convert_anthropic_request_to_openai,
    convert_anthropic_message_to_openai,
    convert_anthropic_tool_to_openai,
    convert_openai_response_to_anthropic
)
from backend.app.core.models import Message, MessageRole, TextContent, ImageContent, ToolDefinition


def test_convert_anthropic_message_text():
    """Test converting Anthropic text message to OpenAI format."""
    anth_message = Message(
        role=MessageRole.USER,
        content="Hello, world!"
    )

    openai_msg = convert_anthropic_message_to_openai(anth_message)
    assert openai_msg["role"] == "user"
    # Simple text content is returned as string for better compatibility
    assert isinstance(openai_msg["content"], str)
    assert openai_msg["content"] == "Hello, world!"


def test_convert_anthropic_message_list():
    """Test converting Anthropic message with content list.

    Note: When there's only a single text block, the converter optimizes
    by returning string format for better compatibility with various providers.
    """
    anth_message = Message(
        role=MessageRole.USER,
        content=[
            {"type": "text", "text": "What's in this image?"}
        ]
    )

    openai_msg = convert_anthropic_message_to_openai(anth_message)
    assert openai_msg["role"] == "user"
    # Single text block is optimized to string format for compatibility
    assert isinstance(openai_msg["content"], str)
    assert openai_msg["content"] == "What's in this image?"



def test_convert_anthropic_message_with_image():
    """Test converting Anthropic message with image."""
    from backend.app.core.models import ImageSource, ImageSourceType
    
    anth_message = Message(
        role=MessageRole.USER,
        content=[
            TextContent(text="Describe this image"),
            ImageContent(
                source=ImageSource(
                    type=ImageSourceType.BASE64,
                    media_type="image/png",
                    data="iVBORw0KGgo..."
                )
            )
        ]
    )
    
    openai_msg = convert_anthropic_message_to_openai(anth_message)
    assert len(openai_msg["content"]) == 2
    assert openai_msg["content"][0]["type"] == "text"
    assert openai_msg["content"][1]["type"] == "image_url"


def test_convert_anthropic_tool():
    """Test converting Anthropic tool to OpenAI format."""
    tool = ToolDefinition(
        name="get_weather",
        description="Get weather",
        input_schema={
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            }
        }
    )
    
    openai_tool = convert_anthropic_tool_to_openai(tool)
    assert openai_tool["type"] == "function"
    assert openai_tool["function"]["name"] == "get_weather"
    assert "parameters" in openai_tool["function"]


def test_convert_anthropic_request():
    """Test converting full Anthropic request to OpenAI format."""
    request = {
        "model": "haiku",
        "messages": [
            {
                "role": "user",
                "content": "Hello"
            }
        ],
        "max_tokens": 100
    }
    
    openai_request = convert_anthropic_request_to_openai(request)
    assert openai_request["model"] == "haiku"
    assert len(openai_request["messages"]) == 1
    assert openai_request["max_tokens"] == 100
    assert openai_request["stream"] == False


def test_convert_anthropic_request_with_tools():
    """Test converting Anthropic request with tools."""
    request = {
        "model": "sonnet",
        "messages": [
            {
                "role": "user",
                "content": "What's the weather?"
            }
        ],
        "max_tokens": 100,
        "tools": [
            {
                "name": "get_weather",
                "description": "Get weather",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    }
    
    openai_request = convert_anthropic_request_to_openai(request)
    assert "tools" in openai_request
    assert len(openai_request["tools"]) == 1
    assert openai_request["tool_choice"] == "auto"


def test_convert_openai_response():
    """Test converting OpenAI response to Anthropic format."""
    openai_response = {
        "id": "chatcmpl-123",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hello, I'm Claude."
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
    
    assert anthropic_response["role"] == "assistant"
    assert "content" in anthropic_response
    assert "usage" in anthropic_response
    assert anthropic_response["usage"]["input_tokens"] == 10
    assert anthropic_response["usage"]["output_tokens"] == 5


def test_model_name_extraction():
    """Test model name extraction from full Anthropic model names."""
    from backend.app.config import Config
    
    config = Config()
    
    # Test short names
    assert config.map_model_name("haiku") == "small"
    assert config.map_model_name("sonnet") == "middle"
    assert config.map_model_name("opus") == "big"
    
    # Test full model names
    assert config.map_model_name("claude-haiku-4-5-20251001") == "small"
    assert config.map_model_name("claude-sonnet-4-5-20250929") == "middle"
    assert config.map_model_name("claude-opus") == "big"
    
    # Test case insensitive
    assert config.map_model_name("Claude-Haiku-4-5-20251001") == "small"
    assert config.map_model_name("CLAUDE-SONNET-4-5-20250929") == "middle"

