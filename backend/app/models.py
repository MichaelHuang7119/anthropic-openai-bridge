"""Data models for Anthropic API compatibility."""
from typing import List, Optional, Union, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum
import re


class MessageRole(str, Enum):
    """Message role types."""
    USER = "user"
    ASSISTANT = "assistant"


class TextContent(BaseModel):
    """Text content block."""
    type: Literal["text"] = "text"
    text: str


class ImageSourceType(str, Enum):
    """Image source type."""
    BASE64 = "base64"
    URL = "url"


class ImageSource(BaseModel):
    """Image source."""
    type: ImageSourceType
    media_type: Optional[str] = Field(None, alias="media_type")
    data: Optional[str] = None
    url: Optional[str] = None


class ImageContent(BaseModel):
    """Image content block."""
    type: Literal["image"] = "image"
    source: ImageSource


class TextDelta(BaseModel):
    """Text delta in streaming response."""
    type: Literal["text_delta"] = "text_delta"
    text: str


class ContentBlock(BaseModel):
    """Content block."""
    type: str
    text: Optional[str] = None
    source: Optional[ImageSource] = None
    name: Optional[str] = None
    input: Optional[Dict[str, Any]] = None
    id: Optional[str] = None  # For tool_use blocks
    model_config = {"extra": "allow"}  # Allow extra fields


class Message(BaseModel):
    """Anthropic message."""
    role: MessageRole
    content: Union[str, List[Union[TextContent, ImageContent, ContentBlock]]]

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        """Validate message content."""
        if isinstance(v, str):
            if len(v) > 100000:  # 100KB limit
                raise ValueError("Message content too long")
            # Check for suspicious patterns
            if '\x00' in v:
                raise ValueError("Message contains null bytes")
        elif isinstance(v, list):
            if len(v) > 100:  # Max 100 content blocks
                raise ValueError("Too many content blocks")
        return v


class ToolDefinition(BaseModel):
    """Tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any] = Field(alias="input_schema")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate tool name."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Tool name cannot be empty")
        if len(v) > 64:
            raise ValueError("Tool name too long")
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError("Tool name must start with letter or underscore, contain only alphanumeric and underscore")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        """Validate tool description."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Tool description cannot be empty")
        if len(v) > 10000:  # Increased from 1000 to 10000 to support longer tool descriptions
            raise ValueError("Tool description too long")
        return v


class MessagesRequest(BaseModel):
    """Anthropic messages request."""
    model: str
    messages: List[Message]
    max_tokens: int
    metadata: Optional[Dict[str, Any]] = None
    stop_sequences: Optional[List[str]] = None
    stream: Optional[bool] = False
    system: Optional[Union[str, List[Union[TextContent, Dict[str, Any]]]]] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    tools: Optional[List[ToolDefinition]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None  # Optional per spec
    container: Optional[Union[str, Dict[str, Any]]] = None  # Optional per spec
    context_management: Optional[Dict[str, Any]] = None  # Optional per spec
    mcp_servers: Optional[List[Dict[str, Any]]] = None  # Optional per spec
    service_tier: Optional[Literal["auto", "standard_only"]] = None  # Optional per spec
    thinking: Optional[Dict[str, Any]] = None  # Optional per spec
    provider: Optional[str] = None  # Optional: specify provider name to use

    model_config = ConfigDict(extra="allow")

    @field_validator("model")
    @classmethod
    def validate_model(cls, v):
        """Validate model name."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Model name cannot be empty")
        if len(v) > 100:
            raise ValueError("Model name too long")
        # Allow alphanumeric, dashes, underscores, and dots
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError("Model name contains invalid characters")
        return v.strip()

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v):
        """Validate max_tokens."""
        if v <= 0:
            raise ValueError("max_tokens must be positive")
        if v > 1000000:  # Increased from 100000 to 1000000 to support larger token limits
            raise ValueError("max_tokens too large")
        return v

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v):
        """Validate temperature."""
        if v is not None and (v < 0 or v > 2):
            raise ValueError("Temperature must be between 0 and 2")
        return v

    @field_validator("top_p")
    @classmethod
    def validate_top_p(cls, v):
        """Validate top_p."""
        if v is not None and (v <= 0 or v > 1):
            raise ValueError("top_p must be between 0 and 1")
        return v

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, v):
        """Validate top_k."""
        if v is not None and v < 1:
            raise ValueError("top_k must be at least 1")
        return v


class TextBlock(BaseModel):
    """Text block in response."""
    type: Literal["text"] = "text"
    text: str
    citations: Optional[Any] = None  # Optional citations field per Anthropic spec


class ToolUseBlock(BaseModel):
    """Tool use block in response."""
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: Dict[str, Any]


class ToolResultBlock(BaseModel):
    """Tool result block."""
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: Union[str, List[TextBlock]]
    is_error: Optional[bool] = False


class MessageResponse(BaseModel):
    """Anthropic message response."""
    id: str
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    content: List[Union[TextBlock, ToolUseBlock]]
    model: str
    stop_reason: Optional[str] = None
    stop_sequence: Optional[str] = None
    usage: Dict[str, int]
    context_management: Optional[Dict[str, Any]] = None  # Optional per spec
    container: Optional[Dict[str, Any]] = None  # Optional per spec


class StreamResponse(BaseModel):
    """Anthropic streaming response."""
    type: str
    delta: Optional[TextDelta] = None
    content_block: Optional[Union[TextBlock, ToolUseBlock]] = None
    content_block_delta: Optional[TextDelta] = None
    message: Optional[MessageResponse] = None
    usage: Optional[Dict[str, int]] = None


class CountTokensRequest(BaseModel):
    """Count tokens request."""
    model: str
    messages: List[Message]


class CountTokensResponse(BaseModel):
    """Count tokens response."""
    model: str
    input_tokens: int

