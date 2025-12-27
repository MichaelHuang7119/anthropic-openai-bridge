"""Base request handler with common functionality for all API formats."""
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any

from ...config import config
from ...core import ModelManager, COST_PER_INPUT_TOKEN, COST_PER_OUTPUT_TOKEN
from ...database import get_database
from ..token_counter import count_tokens_estimate

logger = logging.getLogger(__name__)


class BaseRequestHandler(ABC):
    """Abstract base class for message request handlers.

    Provides common functionality for logging, token tracking, and error handling
    that is shared across different API formats (OpenAI, Anthropic, etc.).
    """

    def __init__(self, model_manager: ModelManager):
        """Initialize the handler with a model manager.

        Args:
            model_manager: The model manager instance for provider/model operations
        """
        self.model_manager = model_manager
        self.observability_config = config.app_config.observability

    def _should_log_sample(self) -> bool:
        """Check if current request should be logged based on sampling rate."""
        import random
        return random.random() < self.observability_config.log_sampling_rate

    def _check_slow_request(
        self, start_time: float, provider_name: str, request_id: str
    ) -> None:
        """Check if request is slow and log warning if enabled.

        Args:
            start_time: The request start time (timestamp)
            provider_name: Name of the provider
            request_id: Unique request identifier
        """
        elapsed_ms = (time.time() - start_time) * 1000
        threshold_ms = self.observability_config.slow_request_threshold_ms

        if elapsed_ms > threshold_ms and self.observability_config.enable_slow_request_alert:
            logger.warning(
                f"Slow request detected: {elapsed_ms:.2f}ms > {threshold_ms}ms threshold, "
                f"provider={provider_name}, request_id={request_id}"
            )

    def _estimate_input_tokens(self, messages: list, model: str) -> int:
        """Estimate input token count from messages.

        Args:
            messages: List of message dictionaries
            model: The model name

        Returns:
            Estimated token count
        """
        return count_tokens_estimate(messages, model)

    async def _log_request(
        self,
        request_id: str,
        provider_name: str,
        model: str,
        request_params: Dict[str, Any],
        response_data: Dict[str, Any] = None,
        status_code: int = 200,
        error_message: str = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        response_time_ms: float = 0.0
    ) -> None:
        """Log request to database.

        Args:
            request_id: Unique request identifier
            provider_name: Name of the provider
            model: Model name
            request_params: Request parameters
            response_data: Response data (optional)
            status_code: HTTP status code
            error_message: Error message if request failed
            input_tokens: Input token count
            output_tokens: Output token count
            response_time_ms: Response time in milliseconds
        """
        db = get_database()
        await db.log_request(
            request_id=request_id,
            provider_name=provider_name,
            model=model,
            request_params=request_params,
            response_data=response_data,
            status_code=status_code,
            error_message=error_message,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            response_time_ms=response_time_ms
        )

    async def _update_token_usage(
        self,
        provider_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_estimate: float = None
    ) -> None:
        """Update token usage statistics.

        Args:
            provider_name: Name of the provider
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            cost_estimate: Estimated cost (optional, calculated if not provided)
        """
        if input_tokens or output_tokens:
            today = datetime.now().strftime("%Y-%m-%d")
            if cost_estimate is None:
                cost_estimate = (
                    (input_tokens or 0) * COST_PER_INPUT_TOKEN +
                    (output_tokens or 0) * COST_PER_OUTPUT_TOKEN
                )
            db = get_database()
            await db.update_token_usage(
                date=today,
                provider_name=provider_name,
                model=model,
                input_tokens=input_tokens or 0,
                output_tokens=output_tokens or 0,
                cost_estimate=cost_estimate
            )

    async def _log_and_update_failed_request(
        self,
        request_id: str,
        provider_name: str,
        model: str,
        request_params: Dict[str, Any],
        input_tokens: int,
        response_time_ms: float,
        error_message: str = None,
        status_code: int = 503
    ) -> None:
        """Log failed request and update token usage.

        Args:
            request_id: Unique request identifier
            provider_name: Name of the provider
            model: Model name
            request_params: Request parameters
            input_tokens: Input token count
            response_time_ms: Response time in milliseconds
            error_message: Error message
            status_code: HTTP status code
        """
        db = get_database()
        await db.log_request(
            request_id=request_id,
            provider_name=provider_name,
            model=model,
            request_params=request_params,
            status_code=status_code,
            error_message=error_message,
            input_tokens=input_tokens,
            output_tokens=0,
            response_time_ms=response_time_ms
        )
        # Update token usage for failed request
        if input_tokens > 0:
            cost_estimate = input_tokens * COST_PER_INPUT_TOKEN
            await db.update_token_usage(
                date=datetime.now().strftime("%Y-%m-%d"),
                provider_name=provider_name,
                model=model,
                input_tokens=input_tokens,
                output_tokens=0,
                cost_estimate=cost_estimate
            )

    @abstractmethod
    async def handle_streaming(
        self,
        req,
        provider_config,
        actual_model: str,
        request_id: str,
        start_time: float
    ):
        """Handle streaming request.

        Args:
            req: The request object
            provider_config: Provider configuration
            actual_model: The actual model name to use
            request_id: Unique request identifier
            start_time: Request start time

        Returns:
            StreamingResponse
        """
        pass

    @abstractmethod
    async def handle_non_streaming(
        self,
        req,
        provider_config,
        actual_model: str,
        request_id: str,
        start_time: float
    ):
        """Handle non-streaming request.

        Args:
            req: The request object
            provider_config: Provider configuration
            actual_model: The actual model name to use
            request_id: Unique request identifier
            start_time: Request start time

        Returns:
            Response dict
        """
        pass
