"""Conversations database operations for chat history management."""

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from datetime import timezone, timedelta

logger = logging.getLogger(__name__)


class ConversationsManager:
    """Manages conversations and messages in the database."""

    def __init__(self, db_core):
        """
        Initialize conversations manager.

        Args:
            db_core: DatabaseCore instance for connection management.
        """
        self.db_core = db_core

    async def create_conversation(
        self,
        user_id: int,
        title: str,
        provider_name: Optional[str] = None,
        api_format: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[int]:
        """
        Create a new conversation.

        Args:
            user_id: User ID who owns this conversation
            title: Conversation title
            provider_name: Provider name
            api_format: API format (openai/anthropic)
            model: Model name

        Returns:
            Conversation ID if successful, None otherwise
        """
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            await cursor.execute(
                """
                INSERT INTO conversations (user_id, title, provider_name, api_format, model)
                VALUES (?, ?, ?, ?, ?)
            """,
                (user_id, title, provider_name, api_format, model),
            )

            await conn.commit()
            conversation_id = cursor.lastrowid
            logger.info(f"Created conversation {conversation_id} for user {user_id}")
            return conversation_id
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            return None

    async def get_conversations(
        self,
        user_id: int,
        limit: Optional[int] = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get conversations for a user.

        Args:
            user_id: User ID
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of conversation records
        """
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            query = """
                SELECT
                    c.id,
                    c.title,
                    c.provider_name,
                    c.api_format,
                    c.model,
                    c.created_at,
                    c.updated_at,
                    (
                        SELECT m.model
                        FROM conversation_messages m
                        WHERE m.conversation_id = c.id
                        AND m.role = 'user'
                        ORDER BY m.id DESC
                        LIMIT 1
                    ) as last_model
                FROM conversations c
                WHERE c.user_id = ?
                ORDER BY c.updated_at DESC
                LIMIT ? OFFSET ?
            """

            await cursor.execute(query, (user_id, limit, offset))
            rows = await cursor.fetchall()

            conversations = []
            # 定义北京时区
            from datetime import timezone, timedelta
            beijing_tz = timezone(timedelta(hours=8))
            for row in rows:
                # 转换时间为北京时间ISO格式
                created_at_beijing = None
                updated_at_beijing = None

                if row["created_at"]:
                    created_at_dt = row["created_at"]
                    if hasattr(created_at_dt, 'isoformat'):
                        # 已经是datetime对象，转换为北京时间
                        beijing_dt = created_at_dt.astimezone(beijing_tz)
                        created_at_beijing = beijing_dt.isoformat()
                    else:
                        # SQLite字符串格式，先解析为UTC，再转北京时间
                        utc_str = str(created_at_dt).replace(' ', 'T') + 'Z'
                        utc_dt = datetime.fromisoformat(utc_str)
                        beijing_dt = utc_dt.astimezone(beijing_tz)
                        created_at_beijing = beijing_dt.isoformat()

                if row["updated_at"]:
                    updated_at_dt = row["updated_at"]
                    if hasattr(updated_at_dt, 'isoformat'):
                        # 已经是datetime对象，转换为北京时间
                        beijing_dt = updated_at_dt.astimezone(beijing_tz)
                        updated_at_beijing = beijing_dt.isoformat()
                    else:
                        # SQLite字符串格式，先解析为UTC，再转北京时间
                        utc_str = str(updated_at_dt).replace(' ', 'T') + 'Z'
                        utc_dt = datetime.fromisoformat(utc_str)
                        beijing_dt = utc_dt.astimezone(beijing_tz)
                        updated_at_beijing = beijing_dt.isoformat()

                conversations.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "provider_name": row["provider_name"],
                        "api_format": row["api_format"],
                        "model": row["model"],
                        "last_model": row["last_model"],
                        "created_at": created_at_beijing,
                        "updated_at": updated_at_beijing,
                    }
                )

            return conversations
        except Exception as e:
            logger.error(f"Failed to get conversations: {e}")
            return []

    async def get_conversation(
        self, conversation_id: int, user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific conversation by ID.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security check)

        Returns:
            Conversation record with messages if found and belongs to user
        """
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            # Get conversation with last user message info
            await cursor.execute(
                """
                SELECT
                    c.id,
                    c.title,
                    c.provider_name,
                    c.api_format,
                    c.model,
                    c.created_at,
                    c.updated_at,
                    (
                        SELECT m.model
                        FROM conversation_messages m
                        WHERE m.conversation_id = c.id
                        AND m.role = 'user'
                        ORDER BY m.id DESC
                        LIMIT 1
                    ) as last_model,
                    (
                        SELECT m.provider_name
                        FROM conversation_messages m
                        WHERE m.conversation_id = c.id
                        AND m.role = 'user'
                        ORDER BY m.id DESC
                        LIMIT 1
                    ) as last_provider_name,
                    (
                        SELECT m.api_format
                        FROM conversation_messages m
                        WHERE m.conversation_id = c.id
                        AND m.role = 'user'
                        ORDER BY m.id DESC
                        LIMIT 1
                    ) as last_api_format
                FROM conversations c
                WHERE c.id = ? AND c.user_id = ?
            """,
                (conversation_id, user_id),
            )

            row = await cursor.fetchone()
            if not row:
                return None

            # 转换时间为北京时间ISO格式
            # 定义北京时区
            from datetime import timezone, timedelta
            beijing_tz = timezone(timedelta(hours=8))
            created_at_beijing = None
            updated_at_beijing = None

            if row["created_at"]:
                created_at_dt = row["created_at"]
                if hasattr(created_at_dt, 'isoformat'):
                    # 已经是datetime对象，转换为北京时间
                    beijing_dt = created_at_dt.astimezone(beijing_tz)
                    created_at_beijing = beijing_dt.isoformat()
                else:
                    # SQLite字符串格式，先解析为UTC，再转北京时间
                    utc_str = str(created_at_dt).replace(' ', 'T') + 'Z'
                    utc_dt = datetime.fromisoformat(utc_str)
                    beijing_dt = utc_dt.astimezone(beijing_tz)
                    created_at_beijing = beijing_dt.isoformat()

            if row["updated_at"]:
                updated_at_dt = row["updated_at"]
                if hasattr(updated_at_dt, 'isoformat'):
                    # 已经是datetime对象，转换为北京时间
                    beijing_dt = updated_at_dt.astimezone(beijing_tz)
                    updated_at_beijing = beijing_dt.isoformat()
                else:
                    # SQLite字符串格式，先解析为UTC，再转北京时间
                    utc_str = str(updated_at_dt).replace(' ', 'T') + 'Z'
                    utc_dt = datetime.fromisoformat(utc_str)
                    beijing_dt = utc_dt.astimezone(beijing_tz)
                    updated_at_beijing = beijing_dt.isoformat()

            conversation = {
                "id": row["id"],
                "title": row["title"],
                "provider_name": row["provider_name"],
                "api_format": row["api_format"],
                "model": row["model"],
                "last_model": row["last_model"],
                "last_provider_name": row["last_provider_name"],
                "last_api_format": row["last_api_format"],
                "created_at": created_at_beijing,
                "updated_at": updated_at_beijing,
                "messages": [],
            }

            # Get messages
            await cursor.execute(
                """
                SELECT id, role, content, model, thinking, input_tokens, output_tokens, created_at, provider_name, api_format, provider_name, api_format
                FROM conversation_messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
            """,
                (conversation_id,),
            )

            message_rows = await cursor.fetchall()
            for msg_row in message_rows:
                # 转换消息时间为北京时间ISO格式
                # 定义北京时区
                beijing_tz = timezone(timedelta(hours=8))
                msg_created_at_beijing = None
                if msg_row["created_at"]:
                    created_at_dt = msg_row["created_at"]
                    if hasattr(created_at_dt, 'isoformat'):
                        # 已经是datetime对象，转换为北京时间
                        beijing_dt = created_at_dt.astimezone(beijing_tz)
                        msg_created_at_beijing = beijing_dt.isoformat()
                    else:
                        # SQLite字符串格式，先解析为UTC，再转北京时间
                        utc_str = str(created_at_dt).replace(' ', 'T') + 'Z'
                        utc_dt = datetime.fromisoformat(utc_str)
                        beijing_dt = utc_dt.astimezone(beijing_tz)
                        msg_created_at_beijing = beijing_dt.isoformat()

                conversation["messages"].append(
                    {
                        "id": msg_row["id"],
                        "role": msg_row["role"],
                        "content": msg_row["content"],
                        "model": msg_row["model"],
                        "thinking": msg_row["thinking"],
                        "input_tokens": msg_row["input_tokens"],
                        "output_tokens": msg_row["output_tokens"],
                        "provider_name": msg_row["provider_name"],
                        "api_format": msg_row["api_format"],
                        "created_at": msg_created_at_beijing,
                    }
                )

            return conversation
        except Exception as e:
            logger.error(f"Failed to get conversation {conversation_id}: {e}")
            return None

    async def update_conversation(
        self, conversation_id: int, user_id: int, title: str
    ) -> bool:
        """
        Update conversation title.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security check)
            title: New title

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            await cursor.execute(
                """
                UPDATE conversations
                SET title = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            """,
                (title, conversation_id, user_id),
            )

            await conn.commit()
            success = cursor.rowcount > 0
            if success:
                logger.info(f"Updated conversation {conversation_id} title")
            return success
        except Exception as e:
            logger.error(f"Failed to update conversation {conversation_id}: {e}")
            return False

    async def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        """
        Delete a conversation and its messages.

        Args:
            conversation_id: Conversation ID
            user_id: User ID (for security check)

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            await cursor.execute(
                """
                DELETE FROM conversations
                WHERE id = ? AND user_id = ?
            """,
                (conversation_id, user_id),
            )

            await conn.commit()
            success = cursor.rowcount > 0
            if success:
                logger.info(f"Deleted conversation {conversation_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id}: {e}")
            return False

    async def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        model: Optional[str] = None,
        thinking: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        provider_name: Optional[str] = None,
        api_format: Optional[str] = None,
    ) -> Optional[int]:
        """
        Add a message to a conversation.

        Args:
            conversation_id: Conversation ID
            role: Message role ('user' or 'assistant')
            content: Message content
            model: Model used for this message
            thinking: Extended thinking content (optional)
            input_tokens: Input token count
            output_tokens: Output token count
            provider_name: Provider used for this message
            api_format: API format for this message (optional)

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            await cursor.execute(
                """
                INSERT INTO conversation_messages
                (conversation_id, role, content, provider_name, model, thinking, input_tokens, output_tokens, api_format)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (conversation_id, role, content, provider_name, model, thinking, input_tokens, output_tokens, api_format),
            )

            # Update conversation updated_at
            await cursor.execute(
                """
                UPDATE conversations
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (conversation_id,),
            )

            await conn.commit()
            message_id = cursor.lastrowid
            logger.debug(f"Added message {message_id} to conversation {conversation_id}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to add message to conversation {conversation_id}: {e}")
            return None

    async def get_messages(
        self, conversation_id: int, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get messages for a conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages (None for all)

        Returns:
            List of message records
        """
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            query = """
                SELECT id, role, content, model, thinking, input_tokens, output_tokens, created_at, provider_name, api_format, provider_name, api_format
                FROM conversation_messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
            """

            params = [conversation_id]

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            await cursor.execute(query, params)
            rows = await cursor.fetchall()

            messages = []
            # 定义北京时区
            from datetime import timezone, timedelta
            beijing_tz = timezone(timedelta(hours=8))
            for row in rows:
                # 转换消息时间为北京时间ISO格式
                created_at_beijing = None
                if row["created_at"]:
                    created_at_dt = row["created_at"]
                    if hasattr(created_at_dt, 'isoformat'):
                        # 已经是datetime对象，转换为北京时间
                        beijing_dt = created_at_dt.astimezone(beijing_tz)
                        created_at_beijing = beijing_dt.isoformat()
                    else:
                        # SQLite字符串格式，先解析为UTC，再转北京时间
                        utc_str = str(created_at_dt).replace(' ', 'T') + 'Z'
                        utc_dt = datetime.fromisoformat(utc_str)
                        beijing_dt = utc_dt.astimezone(beijing_tz)
                        created_at_beijing = beijing_dt.isoformat()

                messages.append(
                    {
                        "id": row["id"],
                        "role": row["role"],
                        "content": row["content"],
                        "model": row["model"],
                        "thinking": row["thinking"],
                        "input_tokens": row["input_tokens"],
                        "output_tokens": row["output_tokens"],
                        "provider_name": row["provider_name"],
                        "api_format": row["api_format"],
                        "created_at": created_at_beijing,
                    }
                )

            return messages
        except Exception as e:
            logger.error(f"Failed to get messages for conversation {conversation_id}: {e}")
            return []

    async def delete_old_conversations(self, days: int = 30) -> int:
        """
        Delete conversations older than specified days.

        Args:
            days: Number of days

        Returns:
            Number of deleted conversations
        """
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            await cursor.execute(
                """
                DELETE FROM conversations
                WHERE updated_at < datetime('now', '-' || ? || ' days')
            """,
                (days,),
            )

            await conn.commit()
            deleted_count = cursor.rowcount
            logger.info(f"Deleted {deleted_count} old conversations")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete old conversations: {e}")
            return 0
