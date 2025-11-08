"""Configuration management for Anthropic OpenAI Bridge"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout: int = 60


class ProviderConfig(BaseModel):
    """Provider configuration."""
    name: str
    enabled: bool = True
    priority: int = 1
    api_key: str
    base_url: str
    api_version: Optional[str] = None
    timeout: int = 180  # Increased from 90 to reduce timeouts for long-running requests
    max_retries: int = 2  # Reduced from 3 to match claude-code-proxy and reduce unnecessary retries
    custom_headers: Dict[str, str] = Field(default_factory=dict)
    models: Dict[str, List[str]] = Field(default_factory=dict)
    max_tokens_limit: Optional[int] = None  # Maximum allowed max_tokens for this provider


class AppConfig(BaseModel):
    """Application configuration."""
    providers: List[ProviderConfig] = Field(default_factory=list)
    fallback_strategy: str = "priority"
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)


class Config:
    """Configuration manager."""
    
    # Model name mappings
    MODEL_MAPPINGS = {
        "haiku": "small",
        "sonnet": "middle",
        "opus": "big"
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration from file."""
        if config_path is None:
            config_path = os.getenv(
                "PROVIDER_CONFIG_PATH",
                str(Path(__file__).parent.parent / "provider.json")
            )
        self.config_path = config_path
        self.app_config = self._load_config()
        
        # Global token limits (per claude-code-proxy pattern)
        # These apply to all requests regardless of provider
        self.max_tokens_limit = int(os.getenv("MAX_TOKENS_LIMIT", "4096"))
        self.min_tokens_limit = int(os.getenv("MIN_TOKENS_LIMIT", "100"))
    
    def _load_config(self) -> AppConfig:
        """Load configuration from JSON file."""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return AppConfig(**data)
    
    def get_enabled_providers(self) -> List[ProviderConfig]:
        """Get list of enabled providers sorted by priority."""
        enabled = [p for p in self.app_config.providers if p.enabled]
        return sorted(enabled, key=lambda x: x.priority)
    
    def resolve_api_key(self, api_key: str) -> str:
        """Resolve environment variable in API key."""
        if api_key.startswith("${") and api_key.endswith("}"):
            var_name = api_key[2:-1]
            return os.getenv(var_name, api_key)
        return api_key
    
    def map_model_name(self, model: str) -> str:
        """
        Map Anthropic model name to provider model category.
        
        Checks if the model name contains 'haiku', 'sonnet', or 'opus' keywords
        and maps them to 'small', 'middle', or 'big' respectively.
        
        Supports various formats:
        - Short names: haiku, sonnet, opus
        - Full names: claude-haiku-4-5-20251001, claude-sonnet-4-5-20250929
        - Any format containing the keywords
        """
        model_lower = model.lower()
        
        # Check if model name contains any of the mapped keywords
        for keyword, category in self.MODEL_MAPPINGS.items():
            if keyword in model_lower:
                return category
        
        # If no mapping found, return the original (lowercased)
        # This allows custom model names to pass through
        return model_lower


# Global config instance
config = Config()

