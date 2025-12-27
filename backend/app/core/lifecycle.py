"""Application lifecycle events (startup/shutdown)."""
import os
import logging

from ..config import config
from ..infrastructure import get_cache_manager
from ..database import get_database
from .auth import hash_password

logger = logging.getLogger(__name__)


async def init_default_admin():
    """Initialize default admin user if not exists."""
    db = get_database()
    
    # Check if any admin user exists
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    
    # Require strong password in production
    if not admin_password:
        import secrets
        admin_password = secrets.token_urlsafe(16)
        logger.warning(
            f"ADMIN_PASSWORD not set! Generated random password: {admin_password}\n"
            "Set ADMIN_PASSWORD environment variable for production."
        )
    elif len(admin_password) < 12:
        logger.warning(
            f"ADMIN_PASSWORD is too short (minimum 12 characters). "
            "Consider using a stronger password in production."
        )
    
    existing_user = await db.get_user_by_email(admin_email)
    if existing_user:
        logger.info(f"Admin user already exists: {admin_email}")
        return
    
    # Create default admin user
    password_hash = hash_password(admin_password)
    user_id = await db.create_user(
        email=admin_email,
        password_hash=password_hash,
        name="Administrator",
        is_admin=True
    )
    
    if user_id:
        logger.info(f"Created default admin user: {admin_email}")
        if not os.getenv("ADMIN_PASSWORD"):
            # In production, use ADMIN_PASSWORD env var. Random password was generated for safety.
            logger.warning("No ADMIN_PASSWORD set. A random password was generated. Set ADMIN_PASSWORD environment variable before using in production!")
        else:
            logger.info("Admin user created with provided password")
    else:
        logger.error("Failed to create default admin user")


async def startup_event():
    """Initialize cache on startup."""
    # Initialize database
    from ..database import initialize_database
    await initialize_database()
    logger.info("Database initialized successfully")
    
    if config.app_config.cache.enabled:
        logger.info("Initializing cache system...")
        cache_manager = get_cache_manager()
        await cache_manager.initialize()
        logger.info("Cache system initialized successfully")
    
    # Initialize default admin user if not exists
    await init_default_admin()
    
    # Start config hot reload
    hot_reload_enabled = os.getenv("CONFIG_HOT_RELOAD", "true").lower() in ("true", "1", "yes")
    if hot_reload_enabled:
        from ..config import start_config_hot_reload
        # Create reload callback that reloads config
        def reload_config():
            try:
                config._load_config()
                logger.info("Configuration hot reloaded successfully")
            except Exception as e:
                logger.error(f"Failed to hot reload configuration: {e}", exc_info=True)
        
        start_config_hot_reload(config.config_path, reload_config)
        logger.info("Configuration hot reload enabled")
    else:
        logger.info("Configuration hot reload disabled (set CONFIG_HOT_RELOAD=false to disable)")


async def shutdown_event():
    """Cleanup resources on shutdown."""
    logger.info("Shutting down and cleaning up resources...")
    
    # Stop config hot reload
    from ..config import stop_config_hot_reload
    stop_config_hot_reload()
    
    # Close cache connections
    from ..infrastructure import close_cache
    await close_cache()
    
    # Close database connections
    from ..database import close_database
    await close_database()
    
    logger.info("Shutdown complete")

