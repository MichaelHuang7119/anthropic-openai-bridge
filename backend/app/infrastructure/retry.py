"""Retry utilities for handling timeout and transient errors."""
import asyncio
import logging
from typing import Callable, TypeVar, Optional, Any
import httpx
from openai import RateLimitError, APIError, APIConnectionError

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def retry_with_backoff(
    func: Callable[[], Any],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (httpx.ReadTimeout, httpx.TimeoutException, APIConnectionError),
    provider_name: Optional[str] = None
) -> Any:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        retryable_exceptions: Tuple of exceptions that should trigger retry
        provider_name: Optional provider name for logging
    
    Returns:
        Result of the function call
        
    Raises:
        Last exception if all retries are exhausted
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except retryable_exceptions as e:
            last_exception = e
            
            if attempt < max_retries:
                # Calculate delay with exponential backoff
                delay = min(initial_delay * (exponential_base ** attempt), max_delay)
                
                provider_info = f" for provider '{provider_name}'" if provider_name else ""
                logger.warning(
                    f"Retryable error{provider_info} (attempt {attempt + 1}/{max_retries + 1}): {type(e).__name__}: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                
                await asyncio.sleep(delay)
            else:
                # All retries exhausted
                provider_info = f" for provider '{provider_name}'" if provider_name else ""
                logger.error(
                    f"All retry attempts exhausted{provider_info}. "
                    f"Last error: {type(e).__name__}: {e}"
                )
                raise
    
    # Should never reach here, but just in case
    if last_exception:
        raise last_exception


def is_retryable_error(exception: Exception) -> bool:
    """
    Check if an exception is retryable.
    
    Args:
        exception: Exception to check
        
    Returns:
        True if the exception is retryable, False otherwise
    """
    retryable_types = (
        httpx.ReadTimeout,
        httpx.TimeoutException,
        httpx.ConnectTimeout,
        httpx.PoolTimeout,
        APIConnectionError,
    )
    
    return isinstance(exception, retryable_types)

