"""Anthropic client wrapper for making direct requests to Anthropic-compatible providers."""
from typing import Optional, Dict, Any, AsyncIterator
import os
import json
import httpx
import logging
from ..config import ProviderConfig
from ..constants import (
    DEFAULT_MAX_KEEPALIVE_CONNECTIONS,
    DEFAULT_MAX_CONNECTIONS,
    DEFAULT_KEEPALIVE_EXPIRY
)

logger = logging.getLogger(__name__)

# Configure httpx limits for connection pooling
# Optimized for high concurrency (10k QPS target)
DEFAULT_LIMITS = httpx.Limits(
    max_keepalive_connections=int(os.getenv("HTTP_MAX_KEEPALIVE_CONNECTIONS", str(DEFAULT_MAX_KEEPALIVE_CONNECTIONS))),
    max_connections=int(os.getenv("HTTP_MAX_CONNECTIONS", str(DEFAULT_MAX_CONNECTIONS))),
    keepalive_expiry=int(os.getenv("HTTP_KEEPALIVE_EXPIRY", str(DEFAULT_KEEPALIVE_EXPIRY)))
)


class AnthropicClient:
    """Wrapper for making direct Anthropic API requests to providers."""
    
    def __init__(self, provider: ProviderConfig):
        """Initialize Anthropic client with provider config."""
        self.provider = provider
        api_key = provider.api_key
        # Resolve environment variable
        if api_key.startswith("${") and api_key.endswith("}"):
            var_name = api_key[2:-1]
            api_key = os.getenv(var_name, "")

        # Configure timeout
        timeout_config = provider.timeout

        # Create httpx client with connection pooling
        # Determine authentication header format
        # Standard Anthropic API uses x-api-key, but some providers may use Authorization Bearer
        base_headers = {
            "Connection": "keep-alive",
            "Content-Type": "application/json",  # Use standard case for consistency
        }
        
        # Check if custom_headers already has Authorization header
        has_custom_auth = provider.custom_headers and (
            "Authorization" in provider.custom_headers or 
            "authorization" in {k.lower(): v for k, v in provider.custom_headers.items()}
        )
        
        # Determine which auth header to use
        # Priority: 1. custom_headers Authorization (if provided), 2. default x-api-key (standard Anthropic API)
        if has_custom_auth:
            # Use custom Authorization header if provided
            logger.debug(f"Using custom Authorization header for {provider.name}")
            # Will be added via custom_headers update below (with API key placeholder replacement)
        else:
            # Standard Anthropic API uses x-api-key
            base_headers["x-api-key"] = api_key
            base_headers["anthropic-version"] = "2023-06-01"  # Anthropic API version
            logger.debug(f"Using x-api-key for {provider.name} (standard Anthropic API)")
        
        # Merge custom headers (may override auth header if provided)
        # Replace ${API_KEY} placeholder in custom headers with actual API key
        # Normalize header keys to standard case (Content-Type, Authorization, etc.)
        if provider.custom_headers:
            processed_custom_headers = {}
            for key, value in provider.custom_headers.items():
                # Normalize header key to standard case
                normalized_key = key.title() if "-" in key else key.capitalize()
                # Special handling for common headers
                if key.lower() == "content-type":
                    normalized_key = "Content-Type"
                elif key.lower() == "authorization":
                    normalized_key = "Authorization"
                
                # Replace ${API_KEY} placeholder with actual API key
                placeholder = "${API_KEY}"
                if isinstance(value, str) and placeholder in value:
                    processed_value = value.replace(placeholder, api_key)
                    processed_custom_headers[normalized_key] = processed_value
                    logger.debug(f"Replaced {placeholder} placeholder in {normalized_key} header for {provider.name}")
                else:
                    processed_custom_headers[normalized_key] = value
            
            # Update base_headers, custom_headers take precedence
            base_headers.update(processed_custom_headers)
        
        self._http_client = httpx.Client(
            timeout=timeout_config,
            limits=DEFAULT_LIMITS,
            headers=base_headers
        )

        # Create async httpx client with connection pooling
        self._async_http_client = httpx.AsyncClient(
            timeout=timeout_config,
            limits=DEFAULT_LIMITS,
            headers=base_headers.copy()
        )
        
        self.base_url = provider.base_url.rstrip('/')
    
    def messages(
        self,
        request: Dict[str, Any],
        stream: bool = False
    ) -> Any:
        """Make Anthropic messages request (synchronous)."""
        url = f"{self.base_url}/v1/messages"
        
        # Prepare request payload
        # Only include fields that the API expects
        # Remove fields that shouldn't be in the request body
        payload = request.copy()
        # Don't include stream in the request body - it's handled by the HTTP client
        # Some APIs may reject requests with unexpected fields
        if "stream" in payload:
            del payload["stream"]
        # Also remove provider field if present (it's for internal routing only)
        if "provider" in payload:
            del payload["provider"]
        
        # Log request details for debugging
        logger.info(
            f"AnthropicClient.messages for {self.provider.name}: "
            f"url={url}, model={payload.get('model')}, "
            f"payload_keys={list(payload.keys())}, "
            f"headers={dict(self._http_client.headers)}"
        )
        logger.debug(f"Full payload: {payload}")
        
        try:
            # Use json=payload which automatically serializes and sets Content-Type
            # This is equivalent to data=json.dumps(payload) but more convenient
            response = self._http_client.post(url, json=payload)
            response.raise_for_status()
            
            if stream:
                # For streaming, return the response object for iteration
                return response
            else:
                # For non-streaming, return parsed JSON
                return response.json()
        except httpx.HTTPStatusError as e:
            # Try to get detailed error message from response
            error_text = ""
            try:
                error_text = str(e.response.text)
                # Try to parse as JSON for better error message
                try:
                    error_json = json.loads(error_text) if error_text else None
                    if error_json and isinstance(error_json, dict):
                        error_msg = error_json.get('error', {}).get('message', '') if isinstance(error_json.get('error'), dict) else error_json.get('message', '')
                        error_detail = error_json.get('detail', '')
                        if error_msg:
                            error_text = f"{error_text} | Error: {error_msg}"
                        elif error_detail:
                            error_text = f"{error_text} | Detail: {error_detail}"
                except:
                    pass
            except:
                error_text = f"Status {e.response.status_code}"
            
            logger.error(
                f"HTTP error from {self.provider.name}: {e.response.status_code} - {error_text} | "
                f"URL: {url} | Model: {payload.get('model')} | Payload keys: {list(payload.keys())}"
            )
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Full error response: {error_text}")
                logger.debug(f"Request payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            raise
        except Exception as e:
            logger.error(f"Error making request to {self.provider.name}: {e}")
            raise
    
    async def messages_async(
        self,
        request: Dict[str, Any],
        stream: bool = False
    ) -> AsyncIterator[Dict[str, Any]]:
        """Make Anthropic messages request (asynchronous).
        
        Returns:
            AsyncIterator[Dict[str, Any]]: For streaming, yields chunks. For non-streaming, yields single response.
        """
        url = f"{self.base_url}/v1/messages"
        
        # Prepare request payload
        # Only include fields that the API expects
        # Remove fields that shouldn't be in the request body
        payload = request.copy()
        # Don't include stream in the request body - it's handled by the HTTP client
        # Some APIs may reject requests with unexpected fields
        if "stream" in payload:
            del payload["stream"]
        # Also remove provider field if present (it's for internal routing only)
        if "provider" in payload:
            del payload["provider"]
        
        try:
            if stream:
                # For streaming, use stream mode
                async with self._async_http_client.stream(
                    "POST",
                    url,
                    json=payload
                ) as response:
                    # Check status before processing stream
                    if response.status_code >= 400:
                        # Read error response before raising
                        try:
                            error_bytes = await response.aread()
                            error_text = error_bytes.decode('utf-8') if isinstance(error_bytes, bytes) else str(error_bytes)
                            # Try to parse as JSON
                            try:
                                error_json = json.loads(error_text) if error_text else None
                                if error_json and isinstance(error_json, dict):
                                    error_msg = error_json.get('error', {}).get('message', '') if isinstance(error_json.get('error'), dict) else error_json.get('message', '')
                                    error_detail = error_json.get('detail', '')
                                    if error_msg:
                                        error_text = f"{error_text} | Error: {error_msg}"
                                    elif error_detail:
                                        error_text = f"{error_text} | Detail: {error_detail}"
                            except:
                                pass
                        except:
                            error_text = f"Status {response.status_code}"
                        
                        logger.error(
                            f"HTTP error from {self.provider.name}: {response.status_code} - {error_text} | "
                            f"URL: {url} | Model: {payload.get('model')} | Payload keys: {list(payload.keys())}"
                        )
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"Full error response: {error_text}")
                            logger.debug(f"Request payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
                        
                        # Raise HTTPStatusError with detailed message
                        response.raise_for_status()
                    
                    # For streaming, yield Server-Sent Events
                    async for line in response.aiter_lines():
                        if line:
                            if line.startswith("data: "):
                                data_str = line[6:]  # Remove "data: " prefix
                                if data_str == "[DONE]":
                                    break
                                try:
                                    yield json.loads(data_str)
                                except json.JSONDecodeError:
                                    continue
                            elif line.startswith("event: "):
                                # Skip event type lines, we'll use type from data
                                continue
            else:
                # For non-streaming, use regular request
                # Log request details for debugging
                logger.info(
                    f"AnthropicClient.messages_async for {self.provider.name}: "
                    f"url={url}, model={payload.get('model')}, "
                    f"payload_keys={list(payload.keys())}, "
                    f"headers={dict(self._async_http_client.headers)}"
                )
                logger.debug(f"Full payload: {payload}")
                response = await self._async_http_client.post(url, json=payload)
                response.raise_for_status()
                # Yield single response
                yield response.json()
        except httpx.HTTPStatusError as e:
            # Try to get detailed error message from response
            error_text = ""
            error_json = None
            try:
                if hasattr(e.response, 'aread'):
                    error_bytes = await e.response.aread()
                    error_text = error_bytes.decode('utf-8') if isinstance(error_bytes, bytes) else str(error_bytes)
                elif hasattr(e.response, 'text'):
                    error_text = str(e.response.text)
                else:
                    error_text = f"Status {e.response.status_code}"
                
                # Try to parse as JSON for better error message
                try:
                    error_json = json.loads(error_text) if error_text else None
                    if error_json:
                        # Extract error message from common formats
                        if isinstance(error_json, dict):
                            error_msg = error_json.get('error', {}).get('message', '') if isinstance(error_json.get('error'), dict) else error_json.get('message', '')
                            error_detail = error_json.get('detail', '')
                            if error_msg:
                                error_text = f"{error_text} | Error: {error_msg}"
                            elif error_detail:
                                error_text = f"{error_text} | Detail: {error_detail}"
                except:
                    pass
            except Exception as read_error:
                error_text = f"Failed to read error response: {read_error}"
            
            logger.error(
                f"HTTP error from {self.provider.name}: {e.response.status_code} - {error_text} | "
                f"URL: {url} | Model: {payload.get('model')} | Payload keys: {list(payload.keys())}"
            )
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Full error response: {error_text}")
                logger.debug(f"Request payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            raise
        except Exception as e:
            logger.error(f"Error making request to {self.provider.name}: {e}")
            raise

    def close(self):
        """Close the HTTP client connections."""
        if hasattr(self, '_http_client'):
            self._http_client.close()

    async def close_async(self):
        """Close the async HTTP client connections."""
        if hasattr(self, '_async_http_client'):
            await self._async_http_client.aclose()

