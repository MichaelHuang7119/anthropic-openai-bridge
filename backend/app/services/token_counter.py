"""Token counting utilities for message token estimation."""
import json
import logging
from typing import List, Dict, Any, Optional
from ..core import Message
from ..infrastructure import OpenAIClient

logger = logging.getLogger(__name__)


def normalize_messages(messages: List[Dict[str, Any]]) -> str:
    """
    Normalize messages to a hashable string for comparison.

    Args:
        messages: List of message dicts

    Returns:
        JSON string representation for hashing/comparison
    """
    # Normalize message format for consistent hashing
    normalized = []
    for msg in messages:
        if isinstance(msg, dict):
            normalized_msg = {
                "role": msg.get("role"),
                "content": msg.get("content")
            }
            normalized.append(normalized_msg)
    return json.dumps(normalized, sort_keys=True)


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
            msg.get("role", "")
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


async def count_tokens_from_history(
    messages: List[Dict[str, Any]],
    provider_name: str,
    model: str,
    db_manager=None
) -> Optional[int]:
    """
    Get token count from historical request logs.

    This function checks if the same messages (or prefix of them) have been
    requested before and returns the cached input_tokens count.

    Args:
        messages: List of message dicts
        provider_name: Provider name
        model: Model name
        db_manager: Database manager instance

    Returns:
        Cached token count if found, None otherwise
    """
    if not db_manager:
        return None

    try:
        # Normalize messages for comparison
        normalized = normalize_messages(messages)

        # Get recent requests with the same provider and model
        request_logs = await db_manager.get_request_logs(
            provider_name=provider_name,
            model=model,
            limit=10  # Check last 10 requests
        )

        if not request_logs:
            return None

        # Try to find matching request
        for log in request_logs:
            if log.get("request_params"):
                try:
                    stored_params = json.loads(log["request_params"]) if isinstance(log["request_params"], str) else log["request_params"]
                    stored_messages = stored_params.get("messages", [])

                    # Check if stored messages match the requested messages
                    stored_normalized = normalize_messages(stored_messages)
                    if stored_normalized == normalized:
                        # Found exact match
                        input_tokens = log.get("input_tokens")
                        if input_tokens is not None and input_tokens > 0:
                            logger.info(f"Found cached token count for {provider_name}/{model}: {input_tokens} tokens")
                            return input_tokens
                except (json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Error parsing stored request params: {e}")
                    continue

        return None
    except Exception as e:
        logger.warning(f"Error checking token history: {e}")
        return None


async def count_tokens_using_api(messages: list, provider: OpenAIClient, model: str) -> int:
    """Count tokens by making a dry-run API call if supported."""
    try:
        # Try to get actual token count by making a minimal request
        # Some providers support this, but for now we'll use estimation
        return count_tokens_estimate(messages, model)
    except Exception as e:
        logger.warning(f"Could not get token count from API: {e}, using estimation")
        return count_tokens_estimate(messages, model)

