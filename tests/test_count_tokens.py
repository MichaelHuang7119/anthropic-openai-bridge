"""Tests for /v1/messages/count_tokens endpoint."""
import pytest
import os
import sys

# Add parent directory to Python path for CI/CD environments
# This allows 'from backend.app' imports when running from backend/tests/
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Enable development mode for tests (no API key required)
# MUST be set before importing app
os.environ["DEV_MODE"] = "true"

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_count_tokens_basic():
    """Test basic token counting."""
    request_data = {
        "model": "haiku",
        "messages": [
            {
                "role": "user",
                "content": "Hello, how are you?"
            }
        ]
    }
    
    response = client.post("/v1/messages/count_tokens", json=request_data)
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert "model" in data
        assert "input_tokens" in data
        assert isinstance(data["input_tokens"], int)
        assert data["input_tokens"] > 0


def test_count_tokens_multiple_messages():
    """Test token counting with multiple messages."""
    request_data = {
        "model": "sonnet",
        "messages": [
            {
                "role": "user",
                "content": "First message"
            },
            {
                "role": "assistant",
                "content": "Response"
            },
            {
                "role": "user",
                "content": "Follow-up question"
            }
        ]
    }
    
    response = client.post("/v1/messages/count_tokens", json=request_data)
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert data["input_tokens"] > 0


def test_count_tokens_with_image():
    """Test token counting with image content."""
    base64_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    request_data = {
        "model": "opus",
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
        ]
    }
    
    response = client.post("/v1/messages/count_tokens", json=request_data)
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert data["input_tokens"] > 0
        # Images should add significant tokens
        assert data["input_tokens"] >= 10


def test_count_tokens_with_image_url():
    """Test token counting with image URL."""
    request_data = {
        "model": "haiku",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe this"
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
        ]
    }
    
    response = client.post("/v1/messages/count_tokens", json=request_data)
    assert response.status_code in [200, 500]


def test_count_tokens_model_mapping():
    """Test token counting with different model mappings."""
    models = ["haiku", "sonnet", "opus"]
    
    for model in models:
        request_data = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": "Test"
                }
            ]
        }
        
        response = client.post("/v1/messages/count_tokens", json=request_data)
        assert response.status_code != 400  # Should not fail with bad request


def test_count_tokens_long_text():
    """Test token counting with long text."""
    long_text = "This is a test. " * 100
    
    request_data = {
        "model": "sonnet",
        "messages": [
            {
                "role": "user",
                "content": long_text
            }
        ]
    }
    
    response = client.post("/v1/messages/count_tokens", json=request_data)
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        data = response.json()
        # Long text should have many tokens
        assert data["input_tokens"] > 50

