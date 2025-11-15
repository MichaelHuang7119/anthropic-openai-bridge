"""Message-related routes."""
import logging
from typing import Union
from fastapi import APIRouter, HTTPException, Depends

from ..core import MessagesRequest, CountTokensRequest, CountTokensResponse, Message, ModelManager
from ..infrastructure import OpenAIClient
from ..auth import require_api_key
from ..services.message_service import MessageService
from ..services.token_counter import count_tokens_estimate, count_tokens_using_api

logger = logging.getLogger(__name__)

router = APIRouter()


def create_messages_router(model_manager: ModelManager) -> APIRouter:
    """Create messages router with dependencies."""
    message_service = MessageService(model_manager)
    
    @router.post("/v1/messages")
    async def messages(
        request: Union[MessagesRequest, dict],
        api_user: dict = Depends(require_api_key())
    ):
        """Handle Anthropic /v1/messages endpoint."""
        return await message_service.handle_messages(request, api_user)
    
    @router.post("/v1/messages/count_tokens")
    async def count_tokens(
        request: Union[CountTokensRequest, dict],
        api_user: dict = Depends(require_api_key())
    ):
        """Handle Anthropic /v1/messages/count_tokens endpoint."""
        try:
            # Parse request
            if isinstance(request, dict):
                req = CountTokensRequest(**request)
            else:
                req = request
            
            # Get provider and model
            provider_config, actual_model = model_manager.get_provider_and_model(req.model)
            client = OpenAIClient(provider_config)
            
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
            
            # Count tokens
            try:
                # Try to get accurate count from API if possible
                token_count = await count_tokens_using_api(
                    messages_list, client, actual_model
                )
            except Exception as e:
                logger.warning(f"Using estimation for token count: {e}")
                token_count = count_tokens_estimate(messages_list, actual_model)
            
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

