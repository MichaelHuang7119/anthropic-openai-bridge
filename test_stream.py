#!/usr/bin/env python3
"""Test script to diagnose streaming issues."""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.infrastructure import OpenAIClient
from app.core import ProviderConfig


async def test_stream():
    """Test streaming from a provider."""
    # Create a test provider config
    provider = ProviderConfig(
        name="test-provider",
        api_key="sk-test",  # Replace with actual key
        base_url="https://api.aiping.work/v1",  # Replace with actual URL
        enabled=True,
        max_retries=1
    )

    client = OpenAIClient(provider)

    # Test request
    params = {
        "model": "Claude-Sonnet-4.5",
        "messages": [{"role": "user", "content": "Hello, say hi!"}],
        "stream": True,
        "max_tokens": 100
    }

    print("Sending streaming request...")
    try:
        stream = await client.chat_completion_async(**params)
        print(f"Stream type: {type(stream)}")
        print(f"Stream object: {stream}")

        chunk_count = 0
        async for chunk in stream:
            chunk_count += 1
            print(f"Chunk {chunk_count}: {chunk}")
            if chunk_count >= 5:  # Limit output
                break

        print(f"Total chunks received: {chunk_count}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_stream())
