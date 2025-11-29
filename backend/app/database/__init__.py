"""Database module - unified database management."""
from typing import Optional
from .core import DatabaseCore
from .encryption import EncryptionManager
from .request_logs import RequestLogsManager
from .health_history import HealthHistoryManager
from .config_changes import ConfigChangesManager
from .token_usage import TokenUsageManager
from .users import UsersManager
from .api_keys import APIKeysManager
from .conversations import ConversationsManager


class DatabaseManager:
    """Unified database manager combining all database operations."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            db_path: Path to database file. If None, uses environment variable or default.
        """
        self.core = DatabaseCore(db_path)
        self.encryption = EncryptionManager()
        self._initialized = False

        # Initialize managers
        self.request_logs = RequestLogsManager(self.core)
        self.health_history = HealthHistoryManager(self.core)
        self.config_changes = ConfigChangesManager(self.core)
        self.token_usage = TokenUsageManager(self.core)
        self.users = UsersManager(self.core)
        self.api_keys = APIKeysManager(self.core)
        self.conversations = ConversationsManager(self.core)
    
    async def initialize(self):
        """Initialize database schema asynchronously."""
        if not self._initialized:
            await self.core.init_database()
            self._initialized = True
    
    async def close(self):
        """Close database connections."""
        await self.core.close()

    def _get_connection(self):
        """Get database connection (for backward compatibility)."""
        return self.core.get_connection()

    def _init_encryption(self):
        """Initialize encryption (for backward compatibility)."""
        # Already initialized in __init__
        pass

    def _init_database(self):
        """Initialize database (for backward compatibility)."""
        # Already initialized in __init__
        pass

    # Delegate methods for backward compatibility
    async def log_request(self, *args, **kwargs):
        """Log a request (delegates to request_logs manager)."""
        return await self.request_logs.log_request(*args, **kwargs)

    async def get_request_logs(self, *args, **kwargs):
        """Get request logs (delegates to request_logs manager)."""
        return await self.request_logs.get_request_logs(*args, **kwargs)

    async def get_request_logs_count(self, *args, **kwargs):
        """Get request logs count (delegates to request_logs manager)."""
        return await self.request_logs.get_request_logs_count(*args, **kwargs)

    async def log_health_status(self, *args, **kwargs):
        """Log health status (delegates to health_history manager)."""
        return await self.health_history.log_health_status(*args, **kwargs)

    async def get_health_history(self, *args, **kwargs):
        """Get health history (delegates to health_history manager)."""
        return await self.health_history.get_health_history(*args, **kwargs)

    async def log_config_change(self, *args, **kwargs):
        """Log config change (delegates to config_changes manager)."""
        return await self.config_changes.log_config_change(*args, **kwargs)

    async def get_config_changes(self, *args, **kwargs):
        """Get config changes (delegates to config_changes manager)."""
        return await self.config_changes.get_config_changes(*args, **kwargs)

    async def update_token_usage(self, *args, **kwargs):
        """Update token usage (delegates to token_usage manager)."""
        return await self.token_usage.update_token_usage(*args, **kwargs)

    async def get_token_usage_summary(self, *args, **kwargs):
        """Get token usage summary (delegates to token_usage manager)."""
        return await self.token_usage.get_token_usage_summary(*args, **kwargs)

    async def create_user(self, *args, **kwargs):
        """Create user (delegates to users manager)."""
        return await self.users.create_user(*args, **kwargs)

    async def get_user_by_email(self, *args, **kwargs):
        """Get user by email (delegates to users manager)."""
        return await self.users.get_user_by_email(*args, **kwargs)

    async def get_user_by_id(self, *args, **kwargs):
        """Get user by ID (delegates to users manager)."""
        return await self.users.get_user_by_id(*args, **kwargs)

    async def update_user_last_login(self, *args, **kwargs):
        """Update user last login (delegates to users manager)."""
        return await self.users.update_user_last_login(*args, **kwargs)

    async def get_user_language(self, *args, **kwargs):
        """Get user language (delegates to users manager)."""
        return await self.users.get_user_language(*args, **kwargs)

    async def update_user_language(self, *args, **kwargs):
        """Update user language (delegates to users manager)."""
        return await self.users.update_user_language(*args, **kwargs)

    async def update_user_password(self, *args, **kwargs):
        """Update user password (delegates to users manager)."""
        return await self.users.update_user_password(*args, **kwargs)

    async def create_api_key(self, *args, **kwargs):
        """Create API key (delegates to api_keys manager)."""
        return await self.api_keys.create_api_key(*args, **kwargs)

    async def get_api_key_by_hash(self, *args, **kwargs):
        """Get API key by hash (delegates to api_keys manager)."""
        return await self.api_keys.get_api_key_by_hash(*args, **kwargs)

    async def get_api_keys(self, *args, **kwargs):
        """Get API keys (delegates to api_keys manager)."""
        return await self.api_keys.get_api_keys(*args, **kwargs)

    async def get_api_keys_count(self, *args, **kwargs):
        """Get API keys count (delegates to api_keys manager)."""
        return await self.api_keys.get_api_keys_count(*args, **kwargs)

    async def update_api_key(self, *args, **kwargs):
        """Update API key (delegates to api_keys manager)."""
        return await self.api_keys.update_api_key(*args, **kwargs)

    async def delete_api_key(self, *args, **kwargs):
        """Delete API key (delegates to api_keys manager)."""
        return await self.api_keys.delete_api_key(*args, **kwargs)

    async def update_api_key_last_used(self, *args, **kwargs):
        """Update API key last used (delegates to api_keys manager)."""
        return await self.api_keys.update_api_key_last_used(*args, **kwargs)

    async def get_api_key_encrypted(self, *args, **kwargs):
        """Get API key encrypted (delegates to api_keys manager)."""
        return await self.api_keys.get_api_key_encrypted(*args, **kwargs)

    @property
    def db_path(self):
        """Get database path (for backward compatibility)."""
        return self.core.db_path

    @property
    def fernet(self):
        """Get fernet instance (for backward compatibility)."""
        return self.encryption.fernet


# Global database instance
_db_instance: Optional[DatabaseManager] = None


def get_database() -> DatabaseManager:
    """Get or create database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance

async def initialize_database():
    """Initialize database asynchronously."""
    db = get_database()
    await db.initialize()
    return db

async def close_database():
    """Close database connections."""
    global _db_instance
    if _db_instance:
        await _db_instance.close()
        _db_instance = None


__all__ = [
    "DatabaseManager",
    "get_database",
    "DatabaseCore",
    "EncryptionManager",
    "RequestLogsManager",
    "HealthHistoryManager",
    "ConfigChangesManager",
    "TokenUsageManager",
    "UsersManager",
    "APIKeysManager",
    "ConversationsManager",
]

