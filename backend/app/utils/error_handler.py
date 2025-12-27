"""Error handling utilities for consistent error responses."""
from typing import Dict, Any, Optional
from fastapi import HTTPException
import httpx
from openai import RateLimitError, APIError, APIConnectionError
from ..core.constants import (
    ERROR_TYPE_RATE_LIMIT,
    ERROR_TYPE_CONNECTION_TIMEOUT,
    ERROR_TYPE_READ_TIMEOUT,
    ERROR_TYPE_CONNECTION_ERROR,
    ERROR_TYPE_TIMEOUT_ERROR,
    ERROR_TYPE_API_ERROR,
    ERROR_TYPE_INTERNAL_ERROR,
)


def create_error_response(
    error_type: str,
    message: str,
    provider: Optional[str] = None,
    retry_count: Optional[int] = None,
    max_retries: Optional[int] = None,
    retry_delay: Optional[float] = None
) -> Dict[str, Any]:
    """Create a standardized error response."""
    error = {
        "type": error_type,
        "message": message
    }
    
    if provider:
        error["provider"] = provider
    if retry_count is not None:
        error["retry_count"] = retry_count
    if max_retries is not None:
        error["max_retries"] = max_retries
    if retry_delay is not None:
        error["retry_delay"] = retry_delay
    
    return {
        "type": "error",
        "error": error
    }


def handle_openai_exception(
    e: Exception,
    provider_name: str,
    raise_http: bool = False
) -> Dict[str, Any]:
    """Handle OpenAI SDK exceptions and convert to standardized error format."""
    if isinstance(e, RateLimitError):
        error_type = ERROR_TYPE_RATE_LIMIT
        message = f"Rate limit exceeded for provider '{provider_name}'. Please try again later."
        status_code = 429
    elif isinstance(e, (httpx.ConnectTimeout, httpx.PoolTimeout)):
        error_type = ERROR_TYPE_CONNECTION_TIMEOUT
        message = f"Unable to connect to provider '{provider_name}'. Connection timeout. Please check your network connection and provider configuration."
        status_code = 503
    elif isinstance(e, APIConnectionError):
        error_type = ERROR_TYPE_CONNECTION_ERROR
        message = f"Connection error to provider '{provider_name}': {str(e)}"
        status_code = 503
    elif isinstance(e, (httpx.ReadTimeout, httpx.TimeoutException)):
        error_type = ERROR_TYPE_TIMEOUT_ERROR
        message = f"Request timeout for provider '{provider_name}'. The request took too long to respond. Please try again or increase the timeout setting."
        status_code = 504
    elif isinstance(e, APIError):
        error_type = ERROR_TYPE_API_ERROR
        message = f"API error from provider '{provider_name}': {str(e)}"
        status_code = 502
    else:
        error_type = ERROR_TYPE_INTERNAL_ERROR
        message = f"Internal error: {str(e)}"
        status_code = 500
    
    error_response = create_error_response(error_type, message, provider=provider_name)
    
    if raise_http:
        raise HTTPException(status_code=status_code, detail=error_response["error"])
    
    return error_response


def create_retry_notification(
    error_type: str,
    message: str,
    provider: str,
    retry_count: int,
    max_retries: int,
    retry_delay: float
) -> Dict[str, Any]:
    """Create a retry notification for streaming responses."""
    return create_error_response(
        error_type=error_type,
        message=message,
        provider=provider,
        retry_count=retry_count,
        max_retries=max_retries,
        retry_delay=retry_delay
    )



