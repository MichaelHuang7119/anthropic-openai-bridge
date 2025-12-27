"""Utility functions for token extraction from various API response formats."""
from typing import Any, Dict, Tuple, Optional


def extract_tokens_from_usage(usage: Any) -> Tuple[Optional[int], Optional[int]]:
    """Extract input and output tokens from usage data with multiple field name support.

    Supports various API response formats:
    - OpenAI: prompt_tokens, completion_tokens
    - Anthropic: input_tokens, output_tokens
    - Other variants: input, output, prompt, completion, etc.

    Args:
        usage: Usage data from API response (dict, object, or None)

    Returns:
        Tuple of (input_tokens, output_tokens)
        - input_tokens: Number of input tokens (None if not found)
        - output_tokens: Number of output tokens (None if not found)
    """
    if usage is None:
        return None, None

    # Convert to dict if needed
    if isinstance(usage, dict):
        usage_dict = usage
    elif hasattr(usage, 'model_dump'):
        usage_dict = usage.model_dump()
    elif hasattr(usage, 'dict'):
        usage_dict = usage.dict()
    elif hasattr(usage, '__dict__'):
        usage_dict = vars(usage)
    else:
        return None, None

    # 常见的 input token 字段名
    input_token_fields = [
        'prompt_tokens',      # OpenAI 格式
        'input_tokens',       # Anthropic 格式
        'prompt',             # 简化格式
        'input',              # 简化格式
        'usage_input_tokens', # 某些 API
        'prompt_tokens_details', # OpenAI 嵌套字段 (特殊处理)
    ]

    # 常见的 output token 字段名
    output_token_fields = [
        'completion_tokens',  # OpenAI 格式
        'output_tokens',      # Anthropic 格式
        'completion',         # 简化格式
        'output',             # 简化格式
        'usage_output_tokens', # 某些 API
        'completion_tokens_details', # OpenAI 嵌套字段 (特殊处理)
    ]

    input_tokens = None
    output_tokens = None

    # 提取 input tokens
    for field in input_token_fields:
        value = usage_dict.get(field)
        if value is not None:
            # 处理嵌套的 completion_tokens_details/prompt_tokens_details
            if isinstance(value, dict):
                nested_value = value.get('cached_tokens') or value.get('tokens') or value.get('total_tokens')
                if nested_value is not None:
                    input_tokens = int(nested_value) if isinstance(nested_value, (int, float)) else None
                    if input_tokens is not None:
                        break
            else:
                input_tokens = int(value) if isinstance(value, (int, float)) else None
                if input_tokens is not None:
                    break

    # 提取 output tokens
    for field in output_token_fields:
        value = usage_dict.get(field)
        if value is not None:
            # 处理嵌套的 completion_tokens_details
            if isinstance(value, dict):
                nested_value = value.get('tokens') or value.get('total_tokens') or value.get('accepted_prediction_tokens')
                if nested_value is not None:
                    output_tokens = int(nested_value) if isinstance(nested_value, (int, float)) else None
                    if output_tokens is not None:
                        break
            else:
                output_tokens = int(value) if isinstance(value, (int, float)) else None
                if output_tokens is not None:
                    break

    return input_tokens, output_tokens


def extract_tokens_from_response(response: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
    """Extract tokens from full API response.

    Args:
        response: Full API response dict

    Returns:
        Tuple of (input_tokens, output_tokens)
    """
    # 尝试从顶层 usage 字段提取
    usage = response.get('usage')
    if usage:
        input_tokens, output_tokens = extract_tokens_from_usage(usage)
        if input_tokens is not None or output_tokens is not None:
            return input_tokens, output_tokens

    # 尝试从顶层直接提取
    input_tokens, output_tokens = extract_tokens_from_usage(response)
    return input_tokens, output_tokens


def update_token_tracking(
    current_input: int,
    current_output: int,
    new_input: Optional[int] = None,
    new_output: Optional[int] = None
) -> Tuple[int, int]:
    """Update token tracking with new values, keeping the maximum.

    Args:
        current_input: Current input token count
        current_output: Current output token count
        new_input: New input token count (if provided)
        new_output: New output token count (if provided)

    Returns:
        Tuple of (updated_input, updated_output)
    """
    updated_input = current_input
    updated_output = current_output

    if new_input is not None and isinstance(new_input, int) and new_input > current_input:
        updated_input = new_input

    if new_output is not None and isinstance(new_output, int) and new_output > current_output:
        updated_output = new_output

    return updated_input, updated_output
