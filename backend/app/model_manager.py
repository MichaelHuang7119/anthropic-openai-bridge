"""Model management for selecting appropriate providers and models."""
from typing import List, Optional, Tuple
import random
from .config import Config, ProviderConfig


class ModelManager:
    """Manages model selection and provider routing."""
    
    def __init__(self, config: Config):
        """Initialize model manager."""
        self.config = config
    
    def get_provider_and_model(
        self, 
        anthropic_model: str
    ) -> Tuple[ProviderConfig, str]:
        """
        Get provider and actual model name for given Anthropic model.
        
        Args:
            anthropic_model: Anthropic model name (haiku, sonnet, opus)
            
        Returns:
            Tuple of (ProviderConfig, actual_model_name)
            
        Raises:
            ValueError: If no suitable provider/model found
        """
        # Map Anthropic model to category
        category = self.config.map_model_name(anthropic_model)
        
        # Get enabled providers
        providers = self.config.get_enabled_providers()
        
        if not providers:
            raise ValueError("No enabled providers available")
        
        # Try each provider in priority order
        for provider in providers:
            if category in provider.models and provider.models[category]:
                # Select a model from the category
                available_models = provider.models[category]
                
                # Use fallback strategy to select model
                if self.config.app_config.fallback_strategy == "priority":
                    model_name = available_models[0]
                elif self.config.app_config.fallback_strategy == "random":
                    model_name = random.choice(available_models)
                else:
                    model_name = available_models[0]
                
                return provider, model_name
        
        raise ValueError(
            f"No provider found with model category '{category}' "
            f"for Anthropic model '{anthropic_model}'"
        )



