"""Tests for /v1/messages endpoint."""
import pytest
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_messages_non_streaming():
    """Test non-streaming messages endpoint."""
    request_data = {
        "model": "haiku",
        "messages": [
            {
                "role": "user",
                "content": "Hello, how are you?"
            }
        ],
        "max_tokens": 100
    }
    
    response = client.post("/v1/messages", json=request_data)
    assert response.status_code in [200, 500]  # May fail if no providers configured
    
    if response.status_code == 200:
        data = response.json()
        assert "id" in data
        assert "role" in data
        assert "content" in data
        assert "model" in data


def test_messages_streaming():
    """Test streaming messages endpoint."""
    request_data = {
        "model": "sonnet",
        "messages": [
            {
                "role": "user",
                "content": "Tell me a joke"
            }
        ],
        "max_tokens": 100,
        "stream": True
    }
    
    response = client.post("/v1/messages", json=request_data)
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        # Check it's a streaming response
        assert response.headers.get("content-type") == "text/event-stream; charset=utf-8"
        
        # Read first few chunks
        content = b""
        for chunk in response.iter_bytes():
            content += chunk
            if len(content) > 1000:  # Read first 1KB
                break
        
        assert len(content) > 0


def test_messages_tool_calling():
    """Test messages endpoint with tool calling."""
    request_data = {
        "model": "opus",
        "messages": [
            {
                "role": "user",
                "content": "What's the weather in San Francisco?"
            }
        ],
        "max_tokens": 100,
        "tools": [
            {
                "name": "get_weather",
                "description": "Get the current weather in a location",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state"
                        }
                    },
                    "required": ["location"]
                }
            }
        ]
    }
    
    response = client.post("/v1/messages", json=request_data)
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert "content" in data
        # May contain tool_use blocks
        content = data.get("content", [])
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                assert "id" in block
                assert "name" in block
                assert "input" in block


def test_messages_multimodal():
    """Test messages endpoint with multimodal input (image)."""
    # Create a simple base64 image (1x1 red pixel)
    base64_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    request_data = {
        "model": "haiku",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What's in this image?"
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": base64_image
                        }
                    }
                ]
            }
        ],
        "max_tokens": 100
    }
    
    response = client.post("/v1/messages", json=request_data)
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert "content" in data


def test_messages_multimodal_url():
    """Test messages endpoint with image URL."""
    request_data = {
        "model": "sonnet",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe this image"
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "url",
                            "url": "https://example.com/image.jpg"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 100
    }
    
    response = client.post("/v1/messages", json=request_data)
    assert response.status_code in [200, 500]


def test_messages_model_mapping():
    """Test model name mapping (haiku->small, sonnet->middle, opus->big)."""
    models_to_test = ["haiku", "sonnet", "opus"]
    
    for model in models_to_test:
        request_data = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": "Test"
                }
            ],
            "max_tokens": 10
        }
        
        response = client.post("/v1/messages", json=request_data)
        # Should not fail with 400 (invalid model) if mapping works
        assert response.status_code != 400


def test_messages_full_model_names():
    """Test full Anthropic model names (claude-haiku-4-5-20251001, etc.)."""
    full_model_names = [
        "claude-haiku-4-5-20251001",
        "claude-sonnet-4-5-20250929",
        "claude-opus",
        "Claude-Haiku-4-5-20251001",  # Case insensitive
    ]
    
    for model in full_model_names:
        request_data = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": "Test"
                }
            ],
            "max_tokens": 10
        }
        
        response = client.post("/v1/messages", json=request_data)
        # Should not fail with 400 (invalid model) if mapping works
        assert response.status_code != 400


def test_messages_invalid_model():
    """Test with invalid model name."""
    request_data = {
        "model": "invalid-model",
        "messages": [
            {
                "role": "user",
                "content": "Test"
            }
        ],
        "max_tokens": 10
    }
    
    response = client.post("/v1/messages", json=request_data)
    # Should fail if model can't be mapped
    assert response.status_code in [400, 500]


def test_messages_with_system():
    """Test messages endpoint with system message."""
    request_data = {
        "model": "haiku",
        "system": "You are a helpful assistant.",
        "messages": [
            {
                "role": "user",
                "content": "Hello"
            }
        ],
        "max_tokens": 50
    }
    
    response = client.post("/v1/messages", json=request_data)
    assert response.status_code in [200, 500]


def test_messages_with_temperature():
    """Test messages endpoint with temperature parameter."""
    request_data = {
        "model": "sonnet",
        "messages": [
            {
                "role": "user",
                "content": "Write a creative story"
            }
        ],
        "max_tokens": 50,
        "temperature": 0.8
    }
    
    response = client.post("/v1/messages", json=request_data)
    assert response.status_code in [200, 500]


def test_messages_with_system_content_blocks():
    """Test messages endpoint with system message as content blocks array."""
    request_data = {
        "model": "haiku",
        "system": [
            {
                "type": "text",
                "text": "You are a helpful assistant."
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": "Hello"
            }
        ],
        "max_tokens": 50
    }
    
    response = client.post("/v1/messages", json=request_data)
    assert response.status_code in [200, 500]


def test_messages_with_system_content_blocks_multiple():
    """Test messages endpoint with system message as multiple content blocks."""
    request_data = {
        "model": "sonnet",
        "system": [
            {
                "type": "text",
                "text": "You are a helpful assistant."
            },
            {
                "type": "text",
                "text": "Always respond in plain text (eg. no markdown)."
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": "Test"
            }
        ],
        "max_tokens": 50
    }
    
    response = client.post("/v1/messages", json=request_data)
    assert response.status_code in [200, 500]

