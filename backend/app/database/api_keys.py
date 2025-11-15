"""API Key management database operations."""
import sqlite3
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class APIKeysManager:
    """Manages API keys in the database."""

    def __init__(self, db_core):
        """
        Initialize API keys manager.

        Args:
            db_core: DatabaseCore instance for connection management.
        """
        self.db_core = db_core

    async def create_api_key(
        self,
        key_hash: str,
        key_prefix: str,
        name: str,
        encrypted_key: Optional[str] = None,
        email: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Optional[int]:
        """Create a new API key."""
        try:
            conn = self.db_core.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO api_keys (key_hash, key_prefix, encrypted_key, name, email, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (key_hash, key_prefix, encrypted_key, name, email, user_id))

            api_key_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"Created API key: {name}")
            return api_key_id
        except sqlite3.IntegrityError:
            logger.error(f"API key already exists")
            return None
        except Exception as e:
            logger.error(f"Failed to create API key: {e}")
            return None

    async def get_api_key_by_hash(self, key_hash: str) -> Optional[Dict[str, Any]]:
        """Get API key by hash."""
        try:
            conn = self.db_core.get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM api_keys WHERE key_hash = ? AND is_active = 1", (key_hash,))
            row = cursor.fetchone()

            conn.close()

            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get API key: {e}")
            return None

    async def get_api_keys(
        self,
        user_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
        name_filter: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Get API keys with optional filters."""
        try:
            conn = self.db_core.get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM api_keys WHERE 1=1"
            params = []

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            if name_filter:
                query += " AND name LIKE ?"
                params.append(f"%{name_filter}%")

            if is_active is not None:
                query += " AND is_active = ?"
                params.append(1 if is_active else 0)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get API keys: {e}")
            return []

    async def get_api_keys_count(
        self,
        user_id: Optional[int] = None,
        name_filter: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> int:
        """Get total count of API keys matching filters."""
        try:
            conn = self.db_core.get_connection()
            cursor = conn.cursor()

            query = "SELECT COUNT(*) as count FROM api_keys WHERE 1=1"
            params = []

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            if name_filter:
                query += " AND name LIKE ?"
                params.append(f"%{name_filter}%")

            if is_active is not None:
                query += " AND is_active = ?"
                params.append(1 if is_active else 0)

            cursor.execute(query, params)
            result = cursor.fetchone()

            conn.close()

            return result["count"] if result else 0
        except Exception as e:
            logger.error(f"Failed to get API keys count: {e}")
            return 0

    async def update_api_key(
        self,
        api_key_id: int,
        name: Optional[str] = None,
        email: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> bool:
        """Update API key."""
        try:
            conn = self.db_core.get_connection()
            cursor = conn.cursor()

            updates = []
            params = []

            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if email is not None:
                updates.append("email = ?")
                params.append(email)
            if is_active is not None:
                updates.append("is_active = ?")
                params.append(is_active)

            if not updates:
                return False

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(api_key_id)

            query = f"UPDATE api_keys SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)

            conn.commit()
            conn.close()

            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update API key: {e}")
            return False

    async def delete_api_key(self, api_key_id: int) -> bool:
        """Delete API key."""
        try:
            conn = self.db_core.get_connection()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM api_keys WHERE id = ?", (api_key_id,))

            conn.commit()
            conn.close()

            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete API key: {e}")
            return False

    async def update_api_key_last_used(self, api_key_id: int):
        """Update API key's last used time."""
        try:
            conn = self.db_core.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE api_keys
                SET last_used_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (api_key_id,))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update API key last used: {e}")

    async def get_api_key_encrypted(self, api_key_id: int) -> Optional[Dict[str, Any]]:
        """获取包含加密完整key的API Key信息"""
        try:
            conn = self.db_core.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM api_keys
                WHERE id = ?
            """, (api_key_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Failed to get encrypted API key: {e}")
            return None

