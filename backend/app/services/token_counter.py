"""Token counting utilities for message token estimation."""
import logging
from typing import List, Dict, Any
from ..core import Message
from ..infrastructure import OpenAIClient

logger = logging.getLogger(__name__)


def count_tokens_estimate(messages: list, model: str) -> int:
    """
    Estimate token count for messages.
    This is a simplified estimation. For accurate counts, you may need
    to use the actual model's tokenizer or call the API.
    """
    # Simple estimation: ~4 characters per token
    total_chars = 0
    for msg in messages:
        if isinstance(msg, dict):
            role = msg.get("role", "")
            content = msg.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            total_chars += len(block.get("text", ""))
                        elif block.get("type") == "image_url":
                            # Images consume tokens based on resolution
                            # Rough estimate: ~85 tokens per image
                            total_chars += 340  # ~85 tokens * 4 chars
            elif isinstance(content, str):
                total_chars += len(content)
        elif isinstance(msg, Message):
            if isinstance(msg.content, str):
                total_chars += len(msg.content)
            elif isinstance(msg.content, list):
                for block in msg.content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            total_chars += len(block.get("text", ""))
                        elif block.get("type") == "image":
                            total_chars += 340
    
    # Add overhead for formatting (role names, etc.)
    overhead = len(messages) * 10
    return int((total_chars / 4) + overhead)


async def count_tokens_using_api(messages: list, provider: OpenAIClient, model: str) -> int:
    """Count tokens by making a dry-run API call if supported."""
    try:
        # Try to get actual token count by making a minimal request
        # Some providers support this, but for now we'll use estimation
        return count_tokens_estimate(messages, model)
    except Exception as e:
        logger.warning(f"Could not get token count from API: {e}, using estimation")
        return count_tokens_estimate(messages, model)

