"""Provider management service."""
import logging
from typing import List, Dict, Any, Optional

from ..services.config_service import ConfigService
from ..config import config

logger = logging.getLogger(__name__)


class ProviderService:
    """Service for managing providers."""

    def __init__(self):
        """Initialize provider service."""
        self.config_service = ConfigService()

    def get_providers(self, include_secrets: bool = False) -> List[Dict[str, Any]]:
        """
        Get all providers.

        Args:
            include_secrets: Whether to include sensitive information like API keys

        Returns:
            List of provider configurations
        """
        try:
            config_data = self.config_service.load_config()
            providers = []

            for p in config_data.get("providers", []):
                provider = {
                    "name": p.get("name"),
                    "enabled": p.get("enabled", True),
                    "priority": p.get("priority", 1),
                    "base_url": p.get("base_url"),
                    "api_version": p.get("api_version"),
                    "timeout": p.get("timeout", 60),
                    "max_retries": p.get("max_retries", 1),
                    "custom_headers": p.get("custom_headers", {}),
                    "models": p.get("models", {}),
                    "api_format": p.get("api_format", "openai")  # Default to 'openai' for backward compatibility
                }

                # Only show API key if explicitly requested
                if include_secrets:
                    provider["api_key"] = p.get("api_key", "")
                else:
                    # Hide API key to protect sensitive information
                    provider["api_key"] = "***" if p.get("api_key") else ""

                providers.append(provider)

            return providers
        except Exception as e:
            logger.error(f"Failed to get providers: {e}")
            raise

    def create_provider(self, provider_data: Dict[str, Any]) -> None:
        """
        Create a new provider.

        Args:
            provider_data: Provider configuration data

        Raises:
            ValueError: If provider already exists or validation fails
        """
        try:
            config_data = self.config_service.load_config()

            # Validate provider name and api_format uniqueness (allow same name with different format)
            for p in config_data.get("providers", []):
                if (p.get("name") == provider_data.get("name") and
                    p.get("api_format") == provider_data.get("api_format")):
                    raise ValueError("Provider with same name and format already exists")

            # Validate provider configuration
            self.config_service.validate_provider_config(provider_data)

            # Ensure api_format is always included (default to 'openai' if not set)
            if "api_format" not in provider_data:
                provider_data["api_format"] = "openai"

            # Add to configuration
            config_data.setdefault("providers", []).append(provider_data)

            # Save configuration
            self.config_service.save_config(config_data)

            # Reload global config to ensure model_manager uses latest config
            config._load_config()

            logger.info(f"Created provider: {provider_data.get('name')}")
        except Exception as e:
            logger.error(f"Failed to create provider: {e}")
            raise

    def update_provider(self, name: str, provider_data: Dict[str, Any], api_format: str = "openai") -> None:
        """
        Update an existing provider.

        Args:
            name: Provider name
            provider_data: Updated provider configuration
            api_format: API format for precise identification

        Raises:
            ValueError: If provider not found or name conflict
        """
        try:
            config_data = self.config_service.load_config()
            providers = config_data.get("providers", [])

            # Find and update provider using name + api_format for precise identification
            target_name = name
            target_format = api_format

            provider_found = False
            for i, p in enumerate(providers):
                if p.get("name") == target_name and p.get("api_format") == target_format:
                    provider_found = True
                    # Check for name and api_format conflict if name or api_format changed
                    new_name = provider_data.get("name", target_name)
                    new_api_format = provider_data.get("api_format", target_format)

                    for j, other in enumerate(providers):
                        if (j != i and
                            other.get("name") == new_name and
                            other.get("api_format") == new_api_format):
                            raise ValueError("Provider with same name and format already exists")

                    # Validate provider configuration
                    self.config_service.validate_provider_config(provider_data)

                    # Log the incoming api_format value for debugging
                    logger.debug(f"Updating provider {name} with format {target_format}: received api_format = {provider_data.get('api_format', 'NOT PROVIDED')}")

                    # Ensure api_format is always included (default to target_format)
                    if "api_format" not in provider_data or provider_data.get("api_format") is None:
                        logger.debug(f"api_format not provided or None, using target_format {target_format}")
                        provider_data["api_format"] = target_format
                    else:
                        logger.debug(f"api_format is set to: {provider_data.get('api_format')}")

                    # Update - preserve existing fields that might not be in provider_data
                    # Merge with existing provider to preserve fields not in the update
                    existing_provider = providers[i].copy()
                    existing_provider.update(provider_data)
                    providers[i] = existing_provider

                    logger.debug(f"Final provider data after update: api_format = {providers[i].get('api_format')}")
                    config_data["providers"] = providers

                    # Save configuration
                    self.config_service.save_config(config_data)

                    # Reload global config
                    config._load_config()

                    logger.info(f"Updated provider: {name} (format: {target_format})")
                    break

            if not provider_found:
                raise ValueError(f"Provider '{name}' with format '{target_format}' not found")
        except Exception as e:
            logger.error(f"Failed to update provider: {e}")
            raise

    def toggle_provider_enabled(self, name: str, enabled: bool, api_format: Optional[str] = None) -> None:
        """
        Toggle provider enabled status.

        Args:
            name: Provider name
            enabled: Enable or disable the provider
            api_format: Optional API format for precise identification

        Raises:
            ValueError: If provider not found
        """
        try:
            config_data = self.config_service.load_config()
            providers = config_data.get("providers", [])

            if api_format:
                # Find specific provider by name + api_format
                for i, p in enumerate(providers):
                    if p.get("name") == name and p.get("api_format") == api_format:
                        providers[i]["enabled"] = enabled
                        config_data["providers"] = providers

                        # Save configuration
                        self.config_service.save_config(config_data)

                        # Reload global config
                        config._load_config()

                        logger.info(f"{'Enabled' if enabled else 'Disabled'} provider: {name} (format: {api_format})")
                        return
                raise ValueError(f"Provider '{name}' with format '{api_format}' not found")
            else:
                # Toggle all providers with the given name
                provider_found = False
                for i, p in enumerate(providers):
                    if p.get("name") == name:
                        providers[i]["enabled"] = enabled
                        provider_found = True

                if provider_found:
                    config_data["providers"] = providers

                    # Save configuration
                    self.config_service.save_config(config_data)

                    # Reload global config
                    config._load_config()

                    logger.info(f"{'Enabled' if enabled else 'Disabled'} all configurations for provider: {name}")
                else:
                    raise ValueError(f"No providers found with name '{name}'")
        except Exception as e:
            logger.error(f"Failed to toggle provider status: {e}")
            raise

    def delete_provider(self, name: str, api_format: Optional[str] = None) -> None:
        """
        Delete a provider.

        Args:
            name: Provider name
            api_format: Optional API format for precise identification

        Raises:
            ValueError: If provider not found
        """
        try:
            config_data = self.config_service.load_config()
            providers = config_data.get("providers", [])

            if api_format:
                # Delete specific provider by name + api_format
                for i, p in enumerate(providers):
                    if p.get("name") == name and p.get("api_format") == api_format:
                        del providers[i]
                        config_data["providers"] = providers

                        # Save configuration
                        self.config_service.save_config(config_data)

                        # Reload global config
                        config._load_config()

                        logger.info(f"Deleted provider: {name} (format: {api_format})")
                        return
                raise ValueError(f"Provider '{name}' with format '{api_format}' not found")
            else:
                # Delete all providers with the given name
                original_count = len(providers)
                providers = [p for p in providers if p.get("name") != name]
                deleted_count = original_count - len(providers)

                if deleted_count > 0:
                    config_data["providers"] = providers

                    # Save configuration
                    self.config_service.save_config(config_data)

                    # Reload global config
                    config._load_config()

                    logger.info(f"Deleted {deleted_count} configuration(s) for provider: {name}")
                else:
                    raise ValueError(f"No providers found with name '{name}'")
        except Exception as e:
            logger.error(f"Failed to delete provider: {e}")
            raise

    def get_provider(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a single provider by name.

        Args:
            name: Provider name

        Returns:
            Provider configuration or None if not found
        """
        try:
            config_data = self.config_service.load_config()
            for p in config_data.get("providers", []):
                if p.get("name") == name:
                    return p
            return None
        except Exception as e:
            logger.error(f"Failed to get provider: {e}")
            raise


