"""OpenAI client wrapper for making requests to providers."""
from typing import Optional, Dict, Any, AsyncIterator
import os
from openai import OpenAI, AsyncOpenAI
from .config import ProviderConfig


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
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=provider.base_url,
            timeout=timeout_config,
            max_retries=provider.max_retries
        )
        
        self.async_client = AsyncOpenAI(
            api_key=api_key,
            base_url=provider.base_url,
            timeout=timeout_config,
            max_retries=provider.max_retries
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
        
        # For streaming requests, include usage data in response
        if stream:
            if "stream_options" not in params:
                params["stream_options"] = {}
            params["stream_options"]["include_usage"] = True
        
        params.update(kwargs)
        
        return await self.async_client.chat.completions.create(**params)

