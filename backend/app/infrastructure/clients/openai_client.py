"""OpenAI client wrapper for making requests to providers."""
from typing import Optional, Dict, Any
import os
import httpx
from openai import OpenAI, AsyncOpenAI
from ...config import ProviderConfig
from ...core.constants import (
    DEFAULT_MAX_KEEPALIVE_CONNECTIONS,
    DEFAULT_MAX_CONNECTIONS,
    DEFAULT_KEEPALIVE_EXPIRY
)

# Configure httpx limits for connection pooling
# Optimized for high concurrency (10k QPS target)
DEFAULT_LIMITS = httpx.Limits(
    max_keepalive_connections=int(os.getenv("HTTP_MAX_KEEPALIVE_CONNECTIONS", str(DEFAULT_MAX_KEEPALIVE_CONNECTIONS))),
    max_connections=int(os.getenv("HTTP_MAX_CONNECTIONS", str(DEFAULT_MAX_CONNECTIONS))),
    keepalive_expiry=int(os.getenv("HTTP_KEEPALIVE_EXPIRY", str(DEFAULT_KEEPALIVE_EXPIRY)))
)


class OpenAIClient:
    """Wrapper for OpenAI client."""
    
    def __init__(self, provider: ProviderConfig):
        """Initialize OpenAI client with provider config."""
        self.provider = provider
        api_key = provider.api_key
        # Resolve environment variable
        if api_key.startswith("${") and api_key.endswith("}"):
            var_name = api_key[2:-1]
            api_key = os.getenv(var_name, "")

        # Configure timeout as a tuple (connect, read, write, pool) for better control
        # Using a single timeout value that applies to all phases
        timeout_config = provider.timeout

        # Create httpx client with connection pooling
        self._http_client = httpx.Client(
            timeout=timeout_config,
            limits=DEFAULT_LIMITS,
            headers={
                "Connection": "keep-alive",
            }
        )

        self.client = OpenAI(
            api_key=api_key,
            base_url=provider.base_url,
            timeout=timeout_config,
            max_retries=provider.max_retries,
            # Use custom http client with connection pooling
            http_client=self._http_client
        )

        # Create async httpx client with connection pooling
        self._async_http_client = httpx.AsyncClient(
            timeout=timeout_config,
            limits=DEFAULT_LIMITS,
            headers={
                "Connection": "keep-alive",
            }
        )

        self.async_client = AsyncOpenAI(
            api_key=api_key,
            base_url=provider.base_url,
            timeout=timeout_config,
            max_retries=provider.max_retries,
            # Use custom http client with connection pooling
            http_client=self._async_http_client
        )
    
    def chat_completion(
        self,
        model: str,
        messages: list,
        stream: bool = False,
        temperature: Optional[float] = None,
        tools: Optional[list] = None,
        **kwargs
    ) -> Any:
        """Make chat completion request."""
        params: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream
        }
        
        if temperature is not None:
            params["temperature"] = temperature
        
        if tools:
            params["tools"] = tools
            # Only set tool_choice if not already provided (allow it to be filtered by main.py)
            if "tool_choice" not in params and "tool_choice" not in kwargs:
                params["tool_choice"] = "auto"
        
        # Filter out enable_thinking for non-streaming calls (modelscope requirement)
        # modelscope API requires enable_thinking to be false (or absent) for non-streaming calls
        if not stream and "enable_thinking" in kwargs:
            enable_thinking_val = kwargs.pop("enable_thinking")
            if enable_thinking_val:
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Removed enable_thinking={enable_thinking_val} for non-streaming call")
        
        params.update(kwargs)
        
        return self.client.chat.completions.create(**params)
    
    async def chat_completion_async(
        self,
        model: str,
        messages: list,
        stream: bool = False,
        temperature: Optional[float] = None,
        tools: Optional[list] = None,
        **kwargs
    ) -> Any:
        """Make async chat completion request."""
        params: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream
        }
        
        if temperature is not None:
            params["temperature"] = temperature
        
        if tools:
            params["tools"] = tools
            # Only set tool_choice if not already provided (allow it to be filtered by main.py)
            if "tool_choice" not in params and "tool_choice" not in kwargs:
                params["tool_choice"] = "auto"
        
        # Filter out enable_thinking for non-streaming calls (modelscope requirement)
        # modelscope API requires enable_thinking to be false (or absent) for non-streaming calls
        if not stream and "enable_thinking" in kwargs:
            enable_thinking_val = kwargs.pop("enable_thinking")
            if enable_thinking_val:
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Removed enable_thinking={enable_thinking_val} for non-streaming call")
        
        # For streaming requests, include usage data in response
        if stream:
            if "stream_options" not in params:
                params["stream_options"] = {}
            params["stream_options"]["include_usage"] = True
        
        params.update(kwargs)
        
        return await self.async_client.chat.completions.create(**params)

    def close(self):
        """Close the HTTP client connections."""
        if hasattr(self, '_http_client') and self._http_client:
            self._http_client.close()

    async def close_async(self):
        """Close the async HTTP client connections."""
        if hasattr(self, '_async_http_client') and self._async_http_client:
            await self._async_http_client.aclose()

