"""Message handling service for processing Anthropic API requests."""
import logging
import time
import uuid
from typing import Optional, Union, List, Dict, Any

from fastapi import HTTPException
import httpx
from openai import RateLimitError, APIError, APIConnectionError

from ..core import MessagesRequest, ModelManager, COLOR_CYAN, COLOR_GREEN, COLOR_YELLOW, COLOR_BLUE, COLOR_MAGENTA, COLOR_WHITE, COLOR_RESET
from ..database import get_database

from .handlers import OpenAIMessageHandler, AnthropicMessageHandler

logger = logging.getLogger(__name__)


class MessageService:
    """Service for handling message requests.

    Delegates to format-specific handlers (OpenAI, Anthropic) for actual processing.
    """

    def __init__(self, model_manager: ModelManager):
        """Initialize the message service.

        Args:
            model_manager: The model manager for provider/model operations
        """
        self.model_manager = model_manager
        self.openai_handler = OpenAIMessageHandler(model_manager)
        self.anthropic_handler = AnthropicMessageHandler(model_manager)

    def _get_user_question(self, req: MessagesRequest) -> str:
        """Extract the user's question from the last user message.

        Args:
            req: The request object

        Returns:
            Truncated user question text
        """
        if req.messages:
            for msg in reversed(req.messages):
                if msg.role == "user":
                    content = msg.content
                    if isinstance(content, str):
                        return content[:200]
                    return str(content)[:200]
        return ""

    async def handle_messages(
        self,
        request: Union[MessagesRequest, dict],
        api_user: dict,
        exclude_providers: Optional[List[str]] = None,
        exclude_models: Optional[Dict[str, List[str]]] = None,
        provider_name: Optional[str] = None,
        api_format: Optional[str] = None,
        session_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        message_id: Optional[str] = None
    ):
        """Handle messages request.

        Routes to appropriate handler based on provider format.

        Args:
            request: The messages request
            api_user: The authenticated user
            exclude_providers: List of provider names to exclude
            exclude_models: Dict of provider names to lists of model names to exclude
            provider_name: Specific provider name to use
            api_format: API format to use
            session_id: Session ID for concurrent request isolation
            chat_id: Chat ID for conversation-level isolation
            message_id: Message ID for message-level isolation

        Returns:
            Response dict or StreamingResponse
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        req = None

        try:
            if isinstance(request, dict):
                req = MessagesRequest(**request)
            else:
                req = request

            user_question = self._get_user_question(req)

            # Case 1: Provider specified - use it directly
            if provider_name:
                return await self._handle_with_specified_provider(
                    req, provider_name, api_format, user_question,
                    request_id, start_time, session_id
                )

            # Case 2: Auto-select provider with fallback
            return await self._handle_with_auto_selection(
                req, user_question, exclude_providers, exclude_models,
                request_id, start_time, session_id
            )

        except HTTPException:
            raise
        except ValueError as e:
            logger.error(f"Value error: {e}")
            await self._log_error(request_id, e, req)
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            await self._log_error(request_id, e, req)
            raise HTTPException(status_code=500, detail="Internal server error")

    async def _handle_with_specified_provider(
        self, req: MessagesRequest, provider_name: str, api_format: str,
        user_question: str, request_id: str, start_time: float, session_id: str
    ):
        """Handle request with explicitly specified provider."""
        # Find matching provider
        matching_providers = [
            p for p in self.model_manager.config.get_enabled_providers()
            if (p.name == provider_name and p.enabled and
                (api_format is None or getattr(p, 'api_format', 'openai').lower() == api_format.lower()))
        ]

        if not matching_providers:
            available_formats = [
                getattr(p, 'api_format', 'openai')
                for p in self.model_manager.config.providers
                if p.name == provider_name and p.enabled
            ]
            raise ValueError(
                f"No enabled provider found for '{provider_name}' with API format '{api_format}'. "
                f"Available formats: {list(set(available_formats))}"
            )

        provider_config = min(matching_providers, key=lambda p: p.priority)
        actual_model = req.model

        # Log request
        import datetime
        session_info = f", Session: {session_id}" if session_id else ""
        provider_api_format = api_format or getattr(provider_config, 'api_format', 'openai').lower()
        start_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        logger.info(
            f"{COLOR_CYAN}[Request {request_id}]{COLOR_RESET}\n"
            f"  {COLOR_GREEN}Started at{COLOR_RESET} {COLOR_YELLOW}{start_timestamp}{COLOR_RESET}\n"
            f"  {COLOR_GREEN}Model{COLOR_RESET}: {COLOR_YELLOW}{actual_model}{COLOR_RESET}\n"
            f"  {COLOR_GREEN}Provider{COLOR_RESET}: {COLOR_BLUE}{provider_config.name}{COLOR_RESET}\n"
            f"  {COLOR_GREEN}API Format{COLOR_RESET}: {COLOR_MAGENTA}{provider_api_format}{COLOR_RESET}\n"
            f"  {COLOR_GREEN}Stream{COLOR_RESET}: {COLOR_WHITE}{req.stream}{COLOR_RESET}\n"
            f"  {COLOR_GREEN}User Question{COLOR_RESET}: {COLOR_YELLOW}{user_question[:200]}{COLOR_RESET}\n"
            f"  {COLOR_GREEN}Mode{COLOR_RESET}: User-specified provider{session_info}"
        )

        # Route to appropriate handler
        if provider_api_format == 'anthropic':
            if req.stream:
                return await self.anthropic_handler.handle_streaming(
                    req, provider_config, actual_model, request_id, start_time
                )
            else:
                return await self.anthropic_handler.handle_non_streaming(
                    req, provider_config, actual_model, request_id, start_time
                )
        else:
            if req.stream:
                return await self.openai_handler.handle_streaming(
                    req, provider_config, actual_model, request_id, start_time
                )
            else:
                return await self.openai_handler.handle_non_streaming(
                    req, provider_config, actual_model, request_id, start_time
                )

    async def _handle_with_auto_selection(
        self, req: MessagesRequest, user_question: str,
        exclude_providers: Optional[List[str]], exclude_models: Optional[Dict],
        request_id: str, start_time: float, session_id: str
    ):
        """Handle request with automatic provider selection and fallback."""
        current_exclude_providers = exclude_providers or []
        current_exclude_models = (exclude_models.copy() if exclude_models else {})
        current_provider_name = None
        failed_models_for_current_provider = []

        while len(current_exclude_providers) < len(self.model_manager.config.get_enabled_providers()):
            try:
                provider_config, actual_model = self.model_manager.get_provider_and_model(
                    req.model,
                    exclude_providers=current_exclude_providers,
                    exclude_models=current_exclude_models,
                    preferred_provider=getattr(req, 'provider', None)
                )

                # Track provider changes
                if current_provider_name is None:
                    current_provider_name = provider_config.name
                    failed_models_for_current_provider = []
                elif current_provider_name != provider_config.name:
                    current_provider_name = provider_config.name
                    failed_models_for_current_provider = []

                # Skip already tried models
                if actual_model in failed_models_for_current_provider:
                    if current_provider_name not in current_exclude_providers:
                        current_exclude_providers.append(current_provider_name)
                    current_provider_name = None
                    failed_models_for_current_provider = []
                    continue

                # Log selection
                import datetime
                session_info = f", Session: {session_id}" if session_id else ""
                provider_api_format = getattr(provider_config, 'api_format', 'openai').lower()
                start_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

                logger.info(
                    f"{COLOR_CYAN}[Request {request_id}]{COLOR_RESET}\n"
                    f"  {COLOR_GREEN}Started at{COLOR_RESET} {COLOR_YELLOW}{start_timestamp}{COLOR_RESET}\n"
                    f"  {COLOR_GREEN}Model{COLOR_RESET}: {COLOR_YELLOW}{actual_model}{COLOR_RESET}\n"
                    f"  {COLOR_GREEN}Provider{COLOR_RESET}: {COLOR_BLUE}{provider_config.name}{COLOR_RESET}\n"
                    f"  {COLOR_GREEN}API Format{COLOR_RESET}: {COLOR_MAGENTA}{provider_api_format}{COLOR_RESET}\n"
                    f"  {COLOR_GREEN}Stream{COLOR_RESET}: {COLOR_WHITE}{req.stream}{COLOR_RESET}\n"
                    f"  {COLOR_GREEN}User Question{COLOR_RESET}: {COLOR_YELLOW}{user_question[:200]}{COLOR_RESET}\n"
                    f"  {COLOR_GREEN}Mode{COLOR_RESET}: Auto-selected provider{session_info}"
                )

                # Route to handler
                api_format = getattr(provider_config, 'api_format', 'openai').lower()
                if api_format == 'anthropic':
                    if req.stream:
                        return await self.anthropic_handler.handle_streaming(
                            req, provider_config, actual_model, request_id, start_time
                        )
                    else:
                        return await self.anthropic_handler.handle_non_streaming(
                            req, provider_config, actual_model, request_id, start_time
                        )
                else:
                    if req.stream:
                        return await self.openai_handler.handle_streaming(
                            req, provider_config, actual_model, request_id, start_time
                        )
                    else:
                        return await self.openai_handler.handle_non_streaming(
                            req, provider_config, actual_model, request_id, start_time
                        )

            except ValueError:
                # No more providers available
                raise ValueError(
                    f"All models exhausted for Anthropic model '{req.model}'. "
                    f"No available models found."
                )

            except (RateLimitError, httpx.ConnectTimeout, httpx.PoolTimeout,
                    APIConnectionError, httpx.ReadTimeout, httpx.TimeoutException,
                    APIError, httpx.HTTPStatusError) as model_error:
                logger.warning(f"Model '{actual_model}' from provider '{provider_config.name}' failed: {type(model_error).__name__}")
                if current_provider_name not in current_exclude_models:
                    current_exclude_models[current_provider_name] = []
                if actual_model not in current_exclude_models[current_provider_name]:
                    current_exclude_models[current_provider_name].append(actual_model)
                    failed_models_for_current_provider.append(actual_model)
                continue

            except HTTPException:
                raise

            except Exception as model_error:
                logger.error(f"Unexpected error: {model_error}", exc_info=True)
                if current_provider_name not in current_exclude_models:
                    current_exclude_models[current_provider_name] = []
                if actual_model not in current_exclude_models[current_provider_name]:
                    current_exclude_models[current_provider_name].append(actual_model)
                    failed_models_for_current_provider.append(actual_model)
                continue

        raise ValueError(f"All providers exhausted for model '{req.model}'")

    async def _log_error(self, request_id: str, error: Exception, req: Optional[MessagesRequest]):
        """Log error to database."""
        try:
            db = get_database()
            model = req.model if req else "unknown"
            request_params = req.model_dump() if req else {}
            await db.log_request(
                request_id=request_id,
                provider_name="unknown",
                model=model,
                request_params={},
                status_code=500,
                error_message=str(error),
                response_time_ms=0
            )
        except Exception:
            pass
