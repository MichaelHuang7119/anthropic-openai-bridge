"""Message-related routes."""
import logging
from typing import Union, Optional
from fastapi import APIRouter, HTTPException, Depends, Header

from ..core import MessagesRequest, CountTokensRequest, CountTokensResponse, Message, ModelManager
from ..infrastructure import OpenAIClient
from ..core.auth import require_api_key
from ..services.message_service import MessageService
from ..services.token_counter import (
    count_tokens_estimate,
    count_tokens_using_api,
    count_tokens_from_history
)

logger = logging.getLogger(__name__)

router = APIRouter()


def create_messages_router(model_manager: ModelManager) -> APIRouter:
    """Create messages router with dependencies."""
    message_service = MessageService(model_manager)

    @router.post("/v1/messages")
    async def messages(
        request: Union[MessagesRequest, dict],
        api_user: dict = Depends(require_api_key()),
        x_provider_name: Optional[str] = Header(None, alias="X-Provider-Name"),
        x_api_format: Optional[str] = Header(None, alias="X-API-Format"),
        x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
        x_chat_id: Optional[str] = Header(None, alias="X-Chat-Id"),
        x_message_id: Optional[str] = Header(None, alias="X-Message-Id")
    ):
        """Handle Anthropic /v1/messages endpoint."""
        logger.info(f"Received request with provider: {x_provider_name}, api_format: {x_api_format}, session_id: {x_session_id}, chat_id: {x_chat_id}, message_id: {x_message_id}")
        return await message_service.handle_messages(
            request,
            api_user,
            provider_name=x_provider_name,
            api_format=x_api_format,
            session_id=x_session_id,
            chat_id=x_chat_id,
            message_id=x_message_id
        )
    
    @router.post("/v1/messages/count_tokens")
    async def count_tokens(
        request: Union[CountTokensRequest, dict],
        api_user: dict = Depends(require_api_key()),
        x_session_id: Optional[str] = Header(None, alias="X-Session-Id")
    ):
        """Handle Anthropic /v1/messages/count_tokens endpoint.

        This endpoint first tries to find token counts from historical request logs,
        then falls back to estimation if no cached value is found.
        """
        logger.info(f"Received count_tokens request with session_id: {x_session_id}")
        try:
            # Parse request
            if isinstance(request, dict):
                req = CountTokensRequest(**request)
            else:
                req = request

            # Get provider and model
            provider_config, actual_model = model_manager.get_provider_and_model(req.model)

            # Convert messages to list of dicts for counting
            messages_list = []
            for msg in req.messages:
                if isinstance(msg, Message):
                    messages_list.append({
                        "role": msg.role.value,
                        "content": msg.content
                    })
                else:
                    messages_list.append(msg)

            # Try to get token count from historical logs first
            token_count = None
            token_source = "cached"  # Default source

            # Try to get from history using database manager
            try:
                from ..database import get_database
                db = get_database()
                cached_count = await count_tokens_from_history(
                    messages_list,
                    provider_config.name,
                    actual_model,
                    db
                )
                if cached_count is not None:
                    token_count = cached_count
                    token_source = "history"
                    logger.info(f"Using cached token count from history: {token_count} tokens")
            except Exception as e:
                logger.debug(f"Could not get token count from history: {e}")

            # If not found in history, try API or fall back to estimation
            if token_count is None:
                try:
                    client = OpenAIClient(provider_config)
                    # Try to get accurate count from API if possible
                    token_count = await count_tokens_using_api(
                        messages_list, client, actual_model
                    )
                    token_source = "api"
                except Exception as e:
                    logger.warning(f"Using estimation for token count: {e}")
                    token_count = count_tokens_estimate(messages_list, actual_model)
                    token_source = "estimated"

            logger.info(
                f"Token count result: {token_count} tokens "
                f"(source: {token_source}, provider: {provider_config.name}, model: {actual_model})"
            )

            return CountTokensResponse(
                model=req.model,
                input_tokens=token_count
            )
        
        except ValueError as e:
            logger.error(f"Value error: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error counting tokens: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    return router

