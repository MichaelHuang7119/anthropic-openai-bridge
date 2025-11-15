"""User management database operations."""
import sqlite3
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
            conn = self.db_core.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO users (email, password_hash, name, is_admin)
                VALUES (?, ?, ?, ?)
            """, (email, password_hash, name, is_admin))

            user_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"Created user: {email}")
            return user_id
        except sqlite3.IntegrityError:
            logger.error(f"User already exists: {email}")
            return None
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        try:
            conn = self.db_core.get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()

            conn.close()

            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            conn = self.db_core.get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()

            conn.close()

            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None

    async def update_user_last_login(self, user_id: int):
        """Update user's last login time."""
        try:
            conn = self.db_core.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users
                SET last_login_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (user_id,))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update user last login: {e}")

