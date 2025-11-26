"""Conversation management API endpoints."""

from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, Query

from ..auth import require_admin

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

class ConversationCreate(BaseModel):
    """Create conversation request model."""
    title: str
    provider_name: str
    api_format: Optional[str] = "openai"
    model: str

class ConversationUpdate(BaseModel):
    """Update conversation request model."""
    title: str

class ConversationResponse(BaseModel):
    """Conversation response model."""
    id: int
    title: str
    provider_name: Optional[str]
    api_format: Optional[str]
    model: Optional[str]
    created_at: str
    updated_at: str

class MessageResponse(BaseModel):
    """Message response model."""
    id: int
    role: str
    content: str
    model: Optional[str]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    created_at: str

class ConversationDetailResponse(BaseModel):
    """Detailed conversation response with messages."""
    id: int
    title: str
    provider_name: Optional[str]
    api_format: Optional[str]
    model: Optional[str]
    created_at: str
    updated_at: str
    messages: List[MessageResponse]

@router.get("", response_model=List[ConversationResponse])
async def get_conversations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(require_admin())
):
    """
    Get conversations for current user.

    Args:
        limit: Maximum number of results (1-200)
        offset: Pagination offset
        user: Current authenticated user
    """
    try:
        from ..database import get_database
        db = get_database()

        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        conversations = await db.conversations.get_conversations(
            user_id=user_id, limit=limit, offset=offset
        )

        return conversations
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversations: {str(e)}")

@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    conversation: ConversationCreate,
    user: dict = Depends(require_admin())
):
    """
    Create a new conversation.

    Args:
        conversation: Conversation creation data
        user: Current authenticated user
    """
    try:
        from ..database import get_database
        db = get_database()

        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        # Create conversation
        conversation_id = await db.conversations.create_conversation(
            user_id=user_id,
            title=conversation.title,
            provider_name=conversation.provider_name,
            api_format=conversation.api_format,
            model=conversation.model
        )

        if not conversation_id:
            raise HTTPException(status_code=500, detail="Failed to create conversation")

        # Get the created conversation
        conversation_data = await db.conversations.get_conversation(conversation_id, user_id)
        if not conversation_data:
            raise HTTPException(status_code=500, detail="Failed to retrieve created conversation")

        return conversation_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")

@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
    user: dict = Depends(require_admin())
):
    """
    Get a specific conversation with messages.

    Args:
        conversation_id: Conversation ID
        user: Current authenticated user
    """
    try:
        from ..database import get_database
        db = get_database()

        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        conversation = await db.conversations.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")

@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    update: ConversationUpdate,
    user: dict = Depends(require_admin())
):
    """
    Update conversation (rename).

    Args:
        conversation_id: Conversation ID
        update: Update data (title)
        user: Current authenticated user
    """
    try:
        from ..database import get_database
        db = get_database()

        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        success = await db.conversations.update_conversation(
            conversation_id, user_id, update.title
        )

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found or update failed")

        # Return updated conversation
        conversation = await db.conversations.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found after update")

        return conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update conversation: {str(e)}")

@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: int,
    user: dict = Depends(require_admin())
):
    """
    Delete a conversation and all its messages.

    Args:
        conversation_id: Conversation ID
        user: Current authenticated user
    """
    try:
        from ..database import get_database
        db = get_database()

        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        success = await db.conversations.delete_conversation(conversation_id, user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found or delete failed")

        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")

@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def add_message(
    conversation_id: int,
    role: str = Query(..., regex="^(user|assistant)$"),
    content: str = Query(..., min_length=1),
    model: Optional[str] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    user: dict = Depends(require_admin())
):
    """
    Add a message to a conversation.

    Args:
        conversation_id: Conversation ID
        role: Message role ('user' or 'assistant')
        content: Message content
        model: Model used
        input_tokens: Input token count
        output_tokens: Output token count
        user: Current authenticated user
    """
    try:
        from ..database import get_database
        db = get_database()

        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        # Verify conversation belongs to user
        conversation = await db.conversations.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Add message
        message_id = await db.conversations.add_message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

        if not message_id:
            raise HTTPException(status_code=500, detail="Failed to add message")

        # Get the created message (simplified retrieval)
        messages = await db.conversations.get_messages(conversation_id)
        for msg in messages:
            if msg["id"] == message_id:
                return msg

        raise HTTPException(status_code=500, detail="Failed to retrieve created message")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add message: {str(e)}")

@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: int,
    limit: Optional[int] = Query(None, ge=1, le=1000),
    user: dict = Depends(require_admin())
):
    """
    Get messages for a conversation.

    Args:
        conversation_id: Conversation ID
        limit: Maximum number of messages
        user: Current authenticated user
    """
    try:
        from ..database import get_database
        db = get_database()

        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")

        # Verify conversation belongs to user
        conversation = await db.conversations.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages = await db.conversations.get_messages(conversation_id, limit)
        return messages
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")
