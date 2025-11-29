"""User management database operations."""
import aiosqlite
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class UsersManager:
    """Manages users in the database."""

    def __init__(self, db_core):
        """
        Initialize users manager.

        Args:
            db_core: DatabaseCore instance for connection management.
        """
        self.db_core = db_core

    async def create_user(
        self,
        email: str,
        password_hash: str,
        name: Optional[str] = None,
        is_admin: bool = True
    ) -> Optional[int]:
        """Create a new user."""
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            await cursor.execute("""
                INSERT INTO users (email, password_hash, name, is_admin)
                VALUES (?, ?, ?, ?)
            """, (email, password_hash, name, is_admin))

            user_id = cursor.lastrowid
            await conn.commit()

            logger.info(f"Created user: {email}")
            return user_id
        except aiosqlite.IntegrityError:
            logger.error(f"User already exists: {email}")
            return None
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            await cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = await cursor.fetchone()

            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            await cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()

            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None

    async def update_user_last_login(self, user_id: int):
        """Update user's last login time."""
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            await cursor.execute("""
                UPDATE users
                SET last_login_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (user_id,))

            await conn.commit()
        except Exception as e:
            logger.error(f"Failed to update user last login: {e}")

    async def get_user_language(self, user_id: int) -> Optional[str]:
        """Get user's language preference."""
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            await cursor.execute("SELECT language FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()

            if row and row['language']:
                return row['language']

            # 如果没有设置语言，返回默认
            return "en-US"
        except Exception as e:
            logger.error(f"Failed to get user language: {e}")
            return "en-US"

    async def update_user_language(self, user_id: int, language: str):
        """Update user's language preference."""
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            await cursor.execute("""
                UPDATE users
                SET language = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (language, user_id))

            await conn.commit()
            logger.info(f"Updated language for user {user_id}: {language}")
        except Exception as e:
            logger.error(f"Failed to update user language: {e}")
            raise

    async def update_user_password(self, user_id: int, password_hash: str):
        """Update user's password."""
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()

            await cursor.execute("""
                UPDATE users
                SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (password_hash, user_id))

            await conn.commit()
            logger.info(f"Updated password for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to update user password: {e}")
            raise

