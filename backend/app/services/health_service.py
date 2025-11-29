"""Health check service for providers."""
import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ..core import MessagesRequest, Message, MessageRole
from ..services.message_service import MessageService
from ..infrastructure import get_circuit_breaker_registry
from ..services.config_service import ConfigService
from ..database.health_history import HealthHistoryManager

logger = logging.getLogger(__name__)


class HealthService:
    """Service for checking provider health status."""

    def __init__(self, message_service: MessageService, health_history_manager: Optional[HealthHistoryManager] = None):
        """
        Initialize health service.

        Args:
            message_service: MessageService instance for testing providers.
            health_history_manager: HealthHistoryManager instance for database operations.
        """
        self.message_service = message_service
        self.config_service = ConfigService()
        self.health_history_manager = health_history_manager

    async def check_provider_health(
        self,
        provider: Dict[str, Any],
        mock_api_user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check health status for a single provider.

        Args:
            provider: Provider configuration
            mock_api_user: Mock API user for health checks

        Returns:
            Health status information
        """
        health_info = {
            "name": provider.get("name"),
            "api_format": provider.get("api_format", "openai"),
            "healthy": None,
            "enabled": provider.get("enabled", True),
            "priority": provider.get("priority", 1),
            "lastCheck": None,
            "responseTime": None,
            "error": None,
            "categories": {}
        }

        # If provider is disabled, mark as unhealthy
        if not provider.get("enabled", True):
            health_info["healthy"] = False
            health_info["error"] = "Provider is disabled"
            for category in ["big", "middle", "small"]:
                health_info["categories"][category] = {
                    "healthy": False,
                    "responseTime": None,
                    "error": "Provider is disabled"
                }
            return health_info

        try:
            # Check circuit breaker status
            registry = get_circuit_breaker_registry()
            breaker = registry.get_breaker(provider.get("name"))
            provider_circuit_open = breaker.state.value == "open"

            # Get all model configurations
            models = provider.get("models", {})

            # Category to Anthropic model name mapping
            category_to_anthropic_model = {
                "big": "opus",
                "middle": "sonnet",
                "small": "haiku"
            }

            # Test all categories in parallel
            category_tasks = [
                self._test_category(
                    category,
                    models.get(category, []),
                    category_to_anthropic_model.get(category),
                    provider.get("name"),
                    provider_circuit_open,
                    mock_api_user
                )
                for category in ["big", "middle", "small"]
            ]
            category_results = await asyncio.gather(*category_tasks)

            # Convert results to dictionary
            category_health = {}
            overall_healthy = False
            overall_response_time = None

            for category, result in category_results:
                category_health[category] = result
                if result["healthy"]:
                    overall_healthy = True
                    if overall_response_time is None:
                        overall_response_time = result["responseTime"]

            health_info["healthy"] = overall_healthy
            health_info["responseTime"] = overall_response_time
            health_info["categories"] = category_health
            health_info["lastCheck"] = datetime.now(timezone.utc).isoformat(timespec='seconds')

            if not overall_healthy:
                errors = []
                for cat, status in category_health.items():
                    if not status.get("healthy") and status.get("error"):
                        errors.append(f"{cat}: {status['error']}")
                if errors:
                    health_info["error"] = "; ".join(errors)[:200]

        except Exception as e:
            health_info["healthy"] = False
            health_info["error"] = str(e)[:200]
            health_info["lastCheck"] = datetime.now(timezone.utc).isoformat(timespec='seconds')
            for category in ["big", "middle", "small"]:
                health_info["categories"][category] = {
                    "healthy": False,
                    "responseTime": None,
                    "error": str(e)[:100]
                }

        return health_info

    async def _test_category(
        self,
        category: str,
        category_models: List[str],
        anthropic_model_name: Optional[str],
        provider_name: str,
        provider_circuit_open: bool,
        mock_api_user: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """Test health status for a single category."""
        if not category_models:
            return category, {
                "healthy": False,
                "responseTime": None,
                "error": "No models configured for this category"
            }

        if provider_circuit_open:
            return category, {
                "healthy": False,
                "responseTime": None,
                "error": "Provider circuit breaker is OPEN"
            }

        if not anthropic_model_name:
            return category, {
                "healthy": False,
                "responseTime": None,
                "error": f"Unknown category: {category}"
            }

        # Try each model in the category until one works
        category_healthy = False
        category_response_time = None
        category_error = None
        excluded_models_for_provider = []

        for model_name in category_models:
            try:
                test_request = MessagesRequest(
                    model=anthropic_model_name,
                    provider=provider_name,
                    messages=[
                        Message(role=MessageRole.USER, content="ping")
                    ],
                    max_tokens=1
                )

                test_start_time = time.time()
                await self.message_service.handle_messages(
                    test_request,
                    mock_api_user,
                    exclude_models={provider_name: excluded_models_for_provider}
                )
                test_response_time = int((time.time() - test_start_time) * 1000)

                category_healthy = True
                category_response_time = test_response_time
                break

            except ValueError as ve:
                # Handle "No provider found" or "All models exhausted" errors
                error_msg = str(ve)
                if "No provider found" in error_msg or "All models exhausted" in error_msg:
                    # All models in this provider are exhausted
                    excluded_models_for_provider.append(model_name)
                    if category_error is None:
                        category_error = f"All models failed. Last error: {error_msg[:200]}"
                    if len(excluded_models_for_provider) >= len(category_models):
                        break
                    continue
                else:
                    # Other ValueError, treat as model failure
                    excluded_models_for_provider.append(model_name)
                    if category_error is None:
                        category_error = f"All models failed. Last error: {error_msg[:200]}"
                    if len(excluded_models_for_provider) >= len(category_models):
                        break
                    continue
            except Exception as model_error:
                excluded_models_for_provider.append(model_name)
                error_msg = str(model_error)
                if hasattr(model_error, 'detail'):
                    if isinstance(model_error.detail, dict):
                        error_detail = model_error.detail.get('message', str(model_error.detail))
                    else:
                        error_detail = str(model_error.detail)
                else:
                    error_detail = str(model_error)

                if category_error is None:
                    category_error = f"All models failed. Last error: {error_detail[:200]}"

                if len(excluded_models_for_provider) >= len(category_models):
                    break
                continue

        return category, {
            "healthy": category_healthy,
            "responseTime": category_response_time,
            "error": category_error if not category_healthy else None
        }

    async def get_all_health_status(self) -> Dict[str, Any]:
        """Get health status for all providers."""
        try:
            config = self.config_service.load_config()
            providers = config.get("providers", [])

            # Create mock API user for health checks
            mock_api_user = {
                "api_key_id": None,
                "name": "health-check",
                "email": None,
                "user_id": None,
                "type": "health-check"
            }

            # Check all providers
            health_data = []
            for provider in providers:
                health_info = await self.check_provider_health(provider, mock_api_user)
                health_data.append(health_info)

            # Calculate overall status
            enabled_providers = [h for h in health_data if h.get("enabled", True)]
            if not enabled_providers:
                overall_status = "error"
            else:
                healthy_providers = [h for h in enabled_providers if h["healthy"] is True]
                unhealthy_providers = [h for h in enabled_providers if h["healthy"] is False]

                if len(healthy_providers) == len(enabled_providers) and len(unhealthy_providers) == 0:
                    overall_status = "healthy"
                elif len(healthy_providers) > 0 and len(unhealthy_providers) > 0:
                    overall_status = "partial"
                elif len(unhealthy_providers) == len(enabled_providers) and len(healthy_providers) == 0:
                    overall_status = "unhealthy"
                else:
                    overall_status = "error"

            return {
                "status": overall_status,
                "timestamp": datetime.now(timezone.utc).isoformat(timespec='seconds'),
                "providers": health_data
            }
        except Exception as e:
            logger.error(f"Failed to get all health status: {e}")
            return {
                "status": "error",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec='seconds'),
                "error": str(e),
                "providers": []
            }

    async def get_provider_health_status(self, provider_name: str) -> Dict[str, Any]:
        """Get health status for a single provider."""
        try:
            config = self.config_service.load_config()
            provider_data = None

            for p in config.get("providers", []):
                if p.get("name") == provider_name:
                    provider_data = p
                    break

            if not provider_data:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Provider not found")

            mock_api_user = {
                "api_key_id": None,
                "name": "health-check",
                "email": None,
                "user_id": None,
                "type": "health-check"
            }

            return await self.check_provider_health(provider_data, mock_api_user)
        except Exception as e:
            logger.error(f"Failed to get provider health status: {e}")
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))

    async def save_health_status_to_db(self, health_data: Dict[str, Any]) -> None:
        """
        Save health check results to database.

        Args:
            health_data: Health status data from get_all_health_status()
        """
        if not self.health_history_manager:
            logger.warning("HealthHistoryManager not available, skipping database save")
            return

        try:
            providers = health_data.get("providers", [])
            for provider in providers:
                provider_name = provider.get("name")
                healthy = provider.get("healthy", False)
                response_time = provider.get("responseTime")
                error = provider.get("error")

                status = "healthy" if healthy else "unhealthy"
                await self.health_history_manager.log_health_status(
                    provider_name=provider_name,
                    status=status,
                    response_time_ms=response_time,
                    error_message=error
                )
            logger.info("Health status saved to database")
        except Exception as e:
            logger.error(f"Failed to save health status to database: {e}")

    async def get_latest_health_from_db(self) -> Optional[Dict[str, Any]]:
        """
        Get the latest health check results from database.

        Returns:
            Health status data in the same format as get_all_health_status() or None if not available.
        """
        if not self.health_history_manager:
            return None

        try:
            # Get the latest health history for each provider
            history = await self.health_history_manager.get_health_history(limit=1000)

            if not history:
                return None

            # Group by provider and get the latest entry
            latest_by_provider = {}
            for entry in history:
                provider_name = entry.get("provider_name")
                if provider_name not in latest_by_provider:
                    latest_by_provider[provider_name] = entry
                else:
                    # Keep the latest (checked_at is already sorted DESC in the query)
                    pass

            # Build provider health data
            provider_health_list = []
            config = self.config_service.load_config()
            providers_config = {p.get("name"): p for p in config.get("providers", [])}

            for provider_name, entry in latest_by_provider.items():
                provider_config = providers_config.get(provider_name, {})
                if not provider_config:
                    continue

                status = entry.get("status", "unhealthy")
                healthy = status == "healthy"

                provider_health_list.append({
                    "name": provider_name,
                    "api_format": provider_config.get("api_format", "openai"),
                    "healthy": healthy,
                    "enabled": provider_config.get("enabled", True),
                    "priority": provider_config.get("priority", 1),
                    "lastCheck": entry.get("checked_at"),
                    "responseTime": entry.get("response_time_ms"),
                    "error": entry.get("error_message"),
                    "categories": {}
                })

            # Calculate overall status
            enabled_providers = [h for h in provider_health_list if h.get("enabled", True)]
            if not enabled_providers:
                overall_status = "error"
            else:
                healthy_providers = [h for h in enabled_providers if h["healthy"] is True]
                unhealthy_providers = [h for h in enabled_providers if h["healthy"] is False]

                if len(healthy_providers) == len(enabled_providers) and len(unhealthy_providers) == 0:
                    overall_status = "healthy"
                elif len(healthy_providers) > 0 and len(unhealthy_providers) > 0:
                    overall_status = "partial"
                elif len(unhealthy_providers) == len(enabled_providers) and len(healthy_providers) == 0:
                    overall_status = "unhealthy"
                else:
                    overall_status = "error"

            # Get the most recent timestamp
            latest_timestamp = max(
                [entry.get("checked_at") for entry in latest_by_provider.values() if entry.get("checked_at")],
                default=None
            )

            return {
                "status": overall_status,
                "timestamp": latest_timestamp or datetime.now(timezone.utc).isoformat(timespec='seconds'),
                "providers": provider_health_list
            }
        except Exception as e:
            logger.error(f"Failed to get health data from database: {e}")
            return None

