"""Configuration management service."""
import json
import os
import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigService:
    """Service for managing provider configuration."""

    @staticmethod
    def get_config_path() -> str:
        """Get provider configuration file path."""
        return os.getenv(
            "PROVIDER_CONFIG_PATH",
            str(Path(__file__).parent.parent.parent / "provider.json")
        )

    @staticmethod
    def load_config() -> Dict[str, Any]:
        """Load provider configuration from file."""
        config_path = ConfigService.get_config_path()
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, returning empty config")
            return {"providers": []}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse config file: {e}")
            raise ValueError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise

    @staticmethod
    def save_config(config_data: Dict[str, Any]) -> None:
        """Save provider configuration to file."""
        config_path = ConfigService.get_config_path()
        try:
            # Ensure directory exists
            config_dir = os.path.dirname(config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Config saved to {config_path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise

    @staticmethod
    def validate_provider_config(provider: Dict[str, Any]) -> bool:
        """Validate provider configuration."""
        required_fields = ["name", "api_key", "base_url", "models"]
        for field in required_fields:
            if field not in provider:
                raise ValueError(f"Missing required field: {field}")
        return True



