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

    async def _execute_query(
        self,
        query: str,
        params: tuple = None,
        fetch_one: bool = False,
        fetch_all: bool = False
    ) -> Optional[Any]:
        """Execute a query with proper resource cleanup.

        Args:
            query: SQL query to execute
            params: Query parameters
            fetch_one: If True, return single row
            fetch_all: If True, return all rows

        Returns:
            Query results based on fetch mode
        """
        cursor = None
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()
            await cursor.execute(query, params or ())

            if fetch_one:
                return await cursor.fetchone()
            elif fetch_all:
                return await cursor.fetchall()
            return None
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            raise
        finally:
            if cursor is not None:
                try:
                    await cursor.close()
                except Exception:
                    pass

    async def _execute_update(
        self,
        query: str,
        params: tuple = None,
        commit: bool = True
    ) -> int:
        """Execute an update/insert/delete query with proper resource cleanup.

        Args:
            query: SQL query to execute
            params: Query parameters
            commit: Whether to commit the transaction

        Returns:
            Number of rows affected or last row id
        """
        cursor = None
        try:
            conn = await self.db_core.get_connection()
            cursor = await conn.cursor()
            await cursor.execute(query, params or ())

            if commit:
                await conn.commit()

            query_upper = query.strip().upper()
            if query_upper.startswith("INSERT"):
                return cursor.lastrowid
            elif query_upper.startswith("UPDATE") or query_upper.startswith("DELETE"):
                return cursor.rowcount
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Database update failed: {e}")
            raise
        finally:
            if cursor is not None:
                try:
                    await cursor.close()
                except Exception:
                    pass

    async def create_user(
        self,
        email: str,
        password_hash: str,
        name: Optional[str] = None,
        is_admin: bool = True
    ) -> Optional[int]:
        """Create a new user.

        Returns:
            User ID if successful, None if user already exists.
        """
        try:
            user_id = await self._execute_update(
                """
                INSERT INTO users (email, password_hash, name, is_admin)
                VALUES (?, ?, ?, ?)
                """,
                (email, password_hash, name, is_admin)
            )
            logger.info(f"Created user: {email}")
            return user_id
        except aiosqlite.IntegrityError:
            logger.error(f"User already exists: {email}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email.

        Returns:
            User dict if found, None otherwise.
        """
        row = await self._execute_query(
            "SELECT * FROM users WHERE email = ?",
            (email,),
            fetch_one=True
        )
        return dict(row) if row else None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID.

        Returns:
            User dict if found, None otherwise.
        """
        row = await self._execute_query(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
            fetch_one=True
        )
        return dict(row) if row else None

    async def update_user_last_login(self, user_id: int) -> None:
        """Update user's last login time."""
        await self._execute_update(
            """
            UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?
            """,
            (user_id,)
        )

    async def get_user_language(self, user_id: int) -> Optional[str]:
        """Get user's language preference.

        Returns:
            Language code if found, "en-US" as default.
        """
        row = await self._execute_query(
            "SELECT language FROM users WHERE id = ?",
            (user_id,),
            fetch_one=True
        )

        if row and row.get('language'):
            return row['language']

        return "en-US"

    async def update_user_language(self, user_id: int, language: str) -> None:
        """Update user's language preference."""
        await self._execute_update(
            """
            UPDATE users SET language = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """,
            (language, user_id)
        )
        logger.info(f"Updated language for user {user_id}: {language}")

    async def update_user_password(self, user_id: int, password_hash: str) -> None:
        """Update user's password."""
        await self._execute_update(
            """
            UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """,
            (password_hash, user_id)
        )
        logger.info(f"Updated password for user {user_id}")
