"""Model management for selecting appropriate providers and models."""
from typing import List, Optional, Tuple, Dict
import random
import logging
from .config import Config, ProviderConfig
from .circuit_breaker import get_circuit_breaker_registry, with_circuit_breaker

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages model selection and provider routing."""
    
    def __init__(self, config: Config):
        """Initialize model manager."""
        self.config = config
    
    def get_provider_and_model(
        self, 
        anthropic_model: str,
        exclude_providers: Optional[List[str]] = None,
        exclude_models: Optional[Dict[str, List[str]]] = None,
        preferred_provider: Optional[str] = None
    ) -> Tuple[ProviderConfig, str]:
        """
        Get provider and actual model name for given Anthropic model.
        
        Rotates through all models in a category within the same provider
        before switching to the next provider.
        
        Args:
            anthropic_model: Anthropic model name (haiku, sonnet, opus)
            exclude_providers: List of provider names to skip
            exclude_models: Dict mapping provider names to lists of model names to skip
            preferred_provider: Optional provider name to use (if specified, only search in this provider)
            
        Returns:
            Tuple of (ProviderConfig, actual_model_name)
            
        Raises:
            ValueError: If no suitable provider/model found
        """
        # Map Anthropic model to category
        category = self.config.map_model_name(anthropic_model)
        
        # Get enabled providers
        all_providers = self.config.get_enabled_providers()
        
        if not all_providers:
            raise ValueError("No enabled providers available")
        
        exclude_providers = exclude_providers or []
        exclude_models = exclude_models or {}
        
        # If preferred_provider is specified, filter to only that provider
        if preferred_provider:
            providers = [p for p in all_providers if p.name == preferred_provider]
            if not providers:
                raise ValueError(f"Preferred provider '{preferred_provider}' not found or not enabled")
        else:
            providers = all_providers
        
        # Try each provider in priority order
        for provider in providers:
            # Skip excluded providers
            if provider.name in exclude_providers:
                logger.debug(f"Skipping provider {provider.name}: excluded")
                continue
                
            # Check if circuit breaker is enabled for this provider
            if self.config.app_config.circuit_breaker.enabled:
                # Skip providers with open circuits
                registry = get_circuit_breaker_registry()
                breaker = registry.get_breaker(provider.name)
                if breaker.state.value == "open":
                    logger.debug(
                        f"Skipping provider {provider.name}: circuit breaker is OPEN"
                    )
                    continue

            if category in provider.models and provider.models[category]:
                # Get all models in the category
                available_models = provider.models[category]
                
                # Get excluded models for this provider
                excluded_for_provider = exclude_models.get(provider.name, [])
                
                # Filter out excluded models
                models_to_try = [m for m in available_models if m not in excluded_for_provider]
                
                if not models_to_try:
                    # All models for this provider are excluded, try next provider
                    logger.debug(
                        f"All models in category '{category}' for provider {provider.name} are excluded"
                    )
                    continue

                # Select a model from the category based on fallback strategy
                # For rotation, we always start from the first available (non-excluded) model
                # The actual rotation happens when failures occur and exclude_models is used
                if self.config.app_config.fallback_strategy == "priority":
                    model_name = models_to_try[0]
                elif self.config.app_config.fallback_strategy == "random":
                    model_name = random.choice(models_to_try)
                else:
                    model_name = models_to_try[0]

                return provider, model_name
        
        raise ValueError(
            f"No provider found with model category '{category}' "
            f"for Anthropic model '{anthropic_model}'"
        )



