"""
Database integration and persistence layer.
Supports SQLite for development and PostgreSQL for production.
"""
import json
import os
import sqlite3
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database manager for persistent storage."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            db_path: Path to database file. If None, uses environment variable or default.
        """
        if db_path is None:
            db_path = os.getenv("DATABASE_PATH", str(Path(__file__).parent.parent / "data" / "app.db"))

        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self.db_path = db_path
        self._init_database()

    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn

    def _init_database(self):
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create request_logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                model TEXT NOT NULL,
                request_params TEXT,
                response_data TEXT,
                status_code INTEGER,
                error_message TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                response_time_ms REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_request_logs_created_at
            ON request_logs(created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_request_logs_provider_model
            ON request_logs(provider_name, model)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_request_logs_request_id
            ON request_logs(request_id)
        """)

        # Create provider_health_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS provider_health_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_name TEXT NOT NULL,
                status TEXT NOT NULL,
                response_time_ms REAL,
                error_message TEXT,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_health_history_provider
            ON provider_health_history(provider_name)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_health_history_checked_at
            ON provider_health_history(checked_at)
        """)

        # Create config_changes table for version control
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                change_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                changed_by TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_config_changes_entity
            ON config_changes(entity_type, entity_name)
        """)

        # Create token_usage table for cost tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                model TEXT NOT NULL,
                request_count INTEGER DEFAULT 0,
                total_input_tokens INTEGER DEFAULT 0,
                total_output_tokens INTEGER DEFAULT 0,
                total_cost_estimate REAL DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, provider_name, model)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_token_usage_date
            ON token_usage(date)
        """)

        # Create users table for admin authentication
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                name TEXT,
                is_admin BOOLEAN DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login_at TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email
            ON users(email)
        """)

        # Create api_keys table for API key management
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_hash TEXT NOT NULL UNIQUE,
                key_prefix TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                user_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                last_used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash
            ON api_keys(key_hash)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_user_id
            ON api_keys(user_id)
        """)

        conn.commit()
        conn.close()

        logger.info(f"Database initialized at {self.db_path}")

    async def log_request(
        self,
        request_id: str,
        provider_name: str,
        model: str,
        request_params: Dict[str, Any],
        response_data: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        response_time_ms: Optional[float] = None
    ):
        """Log a request to the database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO request_logs (
                    request_id, provider_name, model, request_params, response_data,
                    status_code, error_message, input_tokens, output_tokens, response_time_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request_id,
                provider_name,
                model,
                json.dumps(request_params, ensure_ascii=False),
                json.dumps(response_data, ensure_ascii=False) if response_data else None,
                status_code,
                error_message,
                input_tokens,
                output_tokens,
                response_time_ms
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log request: {e}")

    async def log_health_status(
        self,
        provider_name: str,
        status: str,
        response_time_ms: Optional[float] = None,
        error_message: Optional[str] = None
    ):
        """Log provider health status."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO provider_health_history (
                    provider_name, status, response_time_ms, error_message
                ) VALUES (?, ?, ?, ?)
            """, (provider_name, status, response_time_ms, error_message))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log health status: {e}")

    async def log_config_change(
        self,
        change_type: str,
        entity_type: str,
        entity_name: str,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        changed_by: Optional[str] = None
    ):
        """Log a configuration change."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO config_changes (
                    change_type, entity_type, entity_name, old_value, new_value, changed_by
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                change_type,
                entity_type,
                entity_name,
                json.dumps(old_value, ensure_ascii=False) if old_value else None,
                json.dumps(new_value, ensure_ascii=False) if new_value else None,
                changed_by
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log config change: {e}")

    async def update_token_usage(
        self,
        date: str,
        provider_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_estimate: float
    ):
        """Update token usage statistics."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Try to update existing record
            cursor.execute("""
                UPDATE token_usage
                SET request_count = request_count + 1,
                    total_input_tokens = total_input_tokens + ?,
                    total_output_tokens = total_output_tokens + ?,
                    total_cost_estimate = total_cost_estimate + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE date = ? AND provider_name = ? AND model = ?
            """, (input_tokens, output_tokens, cost_estimate, date, provider_name, model))

            # If no rows were updated, insert new record
            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO token_usage (
                        date, provider_name, model, request_count,
                        total_input_tokens, total_output_tokens, total_cost_estimate
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (date, provider_name, model, 1, input_tokens, output_tokens, cost_estimate))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update token usage: {e}")

    async def get_request_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        provider_name: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get request logs with optional filters."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM request_logs WHERE 1=1"
            params = []

            if provider_name:
                query += " AND provider_name = ?"
                params.append(provider_name)

            if date_from:
                query += " AND date(created_at) >= ?"
                params.append(date_from)

            if date_to:
                query += " AND date(created_at) <= ?"
                params.append(date_to)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get request logs: {e}")
            return []

    async def get_token_usage_summary(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get token usage summary."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM token_usage WHERE 1=1"
            params = []

            if date_from:
                query += " AND date >= ?"
                params.append(date_from)

            if date_to:
                query += " AND date <= ?"
                params.append(date_to)

            query += " ORDER BY date DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            conn.close()

            return {
                "summary": [dict(row) for row in rows],
                "total_requests": sum(row["request_count"] for row in rows),
                "total_input_tokens": sum(row["total_input_tokens"] for row in rows),
                "total_output_tokens": sum(row["total_output_tokens"] for row in rows),
                "total_cost_estimate": sum(row["total_cost_estimate"] for row in rows)
            }
        except Exception as e:
            logger.error(f"Failed to get token usage summary: {e}")
            return {"summary": [], "total_requests": 0, "total_input_tokens": 0, "total_output_tokens": 0, "total_cost_estimate": 0}

    async def get_health_history(
        self,
        provider_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get provider health history."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM provider_health_history"
            params = []

            if provider_name:
                query += " WHERE provider_name = ?"
                params.append(provider_name)

            query += " ORDER BY checked_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get health history: {e}")
            return []

    async def get_config_changes(
        self,
        limit: int = 100,
        entity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get configuration changes."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM config_changes"
            params = []

            if entity_type:
                query += " WHERE entity_type = ?"
                params.append(entity_type)

            query += " ORDER BY changed_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get config changes: {e}")
            return []

    # User management methods
    async def create_user(
        self,
        email: str,
        password_hash: str,
        name: Optional[str] = None,
        is_admin: bool = True
    ) -> Optional[int]:
        """Create a new user."""
        try:
            conn = self._get_connection()
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
            conn = self._get_connection()
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
            conn = self._get_connection()
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
            conn = self._get_connection()
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

    # API Key management methods
    async def create_api_key(
        self,
        key_hash: str,
        key_prefix: str,
        name: str,
        email: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Optional[int]:
        """Create a new API key."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO api_keys (key_hash, key_prefix, name, email, user_id)
                VALUES (?, ?, ?, ?, ?)
            """, (key_hash, key_prefix, name, email, user_id))

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
            conn = self._get_connection()
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
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get API keys with optional filters."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM api_keys WHERE 1=1"
            params = []

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get API keys: {e}")
            return []

    async def update_api_key(
        self,
        api_key_id: int,
        name: Optional[str] = None,
        email: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> bool:
        """Update API key."""
        try:
            conn = self._get_connection()
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
            conn = self._get_connection()
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
            conn = self._get_connection()
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


# Global database instance
_db_instance: Optional[DatabaseManager] = None


def get_database() -> DatabaseManager:
    """Get or create database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance