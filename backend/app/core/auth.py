"""
新的认证和授权系统
- 管理面板：邮箱密码登录（JWT Token）
- 服务 API：API Key 验证
- 开发模式：可通过环境变量 DEV_MODE=true 或 --dev 参数启用，开发模式下允许无 API Key 访问
"""
import os
import secrets
import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt

from ..database import get_database

logger = logging.getLogger(__name__)

# Security schemes
security = HTTPBearer(auto_error=False)

# Secret key for JWT - MUST be set via environment variable in production
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(32)
    logger.warning(
        "JWT_SECRET_KEY not set! Generated a random key for this session. "
        "This key will change on restart. Set JWT_SECRET_KEY environment variable for production."
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours default

# Development mode flag (set via environment variable or command line argument)
# WARNING: DEV_MODE should NEVER be enabled in production environments!
# It bypasses all authentication and is a major security risk.
# The environment variable is only read at startup - changes require a restart.
_is_dev_mode_env = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")
# Production check: Disable DEV_MODE if not explicitly allowed
# Set DEV_MODE_ALLOWED_IN_PRODUCTION=true to enable in production (not recommended)
DEV_MODE = _is_dev_mode_env and os.getenv("DEV_MODE_ALLOWED_IN_PRODUCTION", "false").lower() in ("true", "1", "yes")

if _is_dev_mode_env and not DEV_MODE:
    logger.warning(
        "DEV_MODE environment variable is set but DEV_MODE_ALLOWED_IN_PRODUCTION is not enabled. "
        "DEV_MODE has been disabled for security reasons. "
        "If you need to use DEV_MODE in production, set DEV_MODE_ALLOWED_IN_PRODUCTION=true "
        "(WARNING: This is a major security risk and not recommended!)"
    )


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    # Generate salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA256."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a new API key."""
    # Generate a secure random key: sk-{32 random bytes in hex}
    random_bytes = secrets.token_bytes(32)
    return f"sk-{random_bytes.hex()}"


def get_api_key_prefix(api_key: str) -> str:
    """Get the prefix of an API key for display (first 8 chars after sk-)."""
    if api_key.startswith("sk-"):
        return f"sk-{api_key[3:11]}..."
    return api_key[:8] + "..."


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    # Convert user_id to string (python-jose requires sub to be a string)
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token and return user info.

    Returns:
        User info if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        is_admin: bool = payload.get("is_admin", False)

        if user_id_str is None:
            return None

        # Convert sub back to int (it's stored as string in JWT)
        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            logger.warning(f"Invalid user_id in token: {user_id_str}")
            return None

        return {
            "user_id": user_id,
            "is_admin": is_admin,
            "type": "jwt"
        }
    except JWTError as e:
        # Log more specific error information for debugging
        error_type = type(e).__name__
        if "Signature verification failed" in str(e):
            logger.warning("JWT signature verification failed. This may indicate JWT_SECRET_KEY was changed or token is from a different instance.")
        elif "Expired" in str(e) or "expired" in str(e).lower():
            logger.debug(f"JWT token expired: {e}")
        else:
            logger.warning(f"JWT verification error ({error_type}): {e}")
        return None


async def verify_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """
    Verify API key from database and return API key info.
    
    Args:
        api_key: API key to verify
        
    Returns:
        API key info if valid, None otherwise
    """
    try:
        db = get_database()
        key_hash = hash_api_key(api_key)
        api_key_data = await db.get_api_key_by_hash(key_hash)
        
        if not api_key_data:
            return None
        
        # Update last used time
        await db.update_api_key_last_used(api_key_data["id"])
        
        return {
            "api_key_id": api_key_data["id"],
            "name": api_key_data["name"],
            "email": api_key_data["email"],
            "user_id": api_key_data["user_id"],
            "type": "api_key"
        }
    except Exception as e:
        logger.error(f"Failed to verify API key: {e}")
        return None


async def get_current_admin_user(
    credentials: Optional[HTTPAuthorizationCredentials] = None,
    request: Optional[Request] = None
) -> Dict[str, Any]:
    """
    Get current authenticated admin user (for management panel).
    Only accepts JWT tokens from email/password login.

    In development mode (DEV_MODE=true), allows access without authentication.

    Raises:
        HTTPException: If authentication fails or user is not admin
    """
    # Development mode: allow access without validation
    if DEV_MODE:
        logger.info("Development mode: Allowing admin access without authentication")
        return {
            "user_id": 1,  # Default to admin user ID 1
            "email": "admin@example.com",
            "name": "Administrator",
            "is_admin": True,
            "type": "dev"
        }

    # Try Bearer token (JWT)
    if credentials:
        token = credentials.credentials
        user = verify_jwt_token(token)
        if user:
            # Verify user is admin and active
            db = get_database()
            user_data = await db.get_user_by_id(user["user_id"])
            if user_data and user_data.get("is_active") and user_data.get("is_admin"):
                return {
                    "user_id": user_data["id"],
                    "email": user_data["email"],
                    "name": user_data["name"],
                    "is_admin": True,
                    "type": "jwt"
                }
        else:
            logger.warning("JWT token verification failed")
    elif request:
        # Check if Authorization header exists but wasn't parsed by HTTPBearer
        auth_header = request.headers.get("Authorization")
        if auth_header:
            # Try to extract token manually
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                user = verify_jwt_token(token)
                if user:
                    db = get_database()
                    user_data = await db.get_user_by_id(user["user_id"])
                    if user_data and user_data.get("is_active") and user_data.get("is_admin"):
                        logger.info("Successfully authenticated using manual token extraction")
                        return {
                            "user_id": user_data["id"],
                            "email": user_data["email"],
                            "name": user_data["name"],
                            "is_admin": True,
                            "type": "jwt"
                        }
                else:
                    logger.warning("Manual token extraction failed")
            else:
                logger.warning("Authorization header has invalid format")
        else:
            logger.warning("No Authorization header found in request")
    
    # Try API key from header (for backward compatibility, but should use JWT for admin)
    if request:
        api_key = request.headers.get("X-API-Key")
        if api_key:
            api_key_data = await verify_api_key(api_key)
            if api_key_data:
                # Check if associated user is admin
                if api_key_data.get("user_id"):
                    db = get_database()
                    user_data = await db.get_user_by_id(api_key_data["user_id"])
                    if user_data and user_data.get("is_active") and user_data.get("is_admin"):
                        return {
                            "user_id": user_data["id"],
                            "email": user_data["email"],
                            "name": user_data["name"],
                            "is_admin": True,
                            "type": "api_key"
                        }
    
    # Authentication required
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated or insufficient permissions",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_api_user(
    credentials: Optional[HTTPAuthorizationCredentials] = None,
    request: Optional[Request] = None
) -> Dict[str, Any]:
    """
    Get current authenticated API user (for service API).
    Accepts both API keys and JWT tokens (for admin users).

    In development mode (DEV_MODE=true), allows access without API key or with any API key string.
    No validation is performed in development mode.

    Optimization: If an API key is provided but invalid, return error immediately
    instead of trying other authentication methods.

    Raises:
        HTTPException: If authentication fails (only in production mode)
    """
    # Development mode: allow access without validation
    if DEV_MODE:
        logger.info("Development mode: Allowing access without API key validation")
        return {
            "api_key_id": None,
            "name": "dev-user",
            "email": None,
            "user_id": None,
            "type": "dev"
        }

    # Production mode: require valid API key or JWT token
    # Try API key from header first
    if request:
        api_key = request.headers.get("X-API-Key")
        if api_key:
            api_key_data = await verify_api_key(api_key)
            if api_key_data:
                return api_key_data
            # API key was provided but invalid - return error immediately
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={
                    "WWW-Authenticate": "Bearer",
                    "Retry-After": "0",  # Tell client not to retry authentication errors
                },
            )

        # Try API key from query parameter
        api_key = request.query_params.get("api_key")
        if api_key:
            api_key_data = await verify_api_key(api_key)
            if api_key_data:
                return api_key_data
            # API key was provided but invalid - return error immediately
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={
                    "WWW-Authenticate": "Bearer",
                    "Retry-After": "0",  # Tell client not to retry authentication errors
                },
            )

    # Try Bearer token (could be API key or JWT token)
    if credentials:
        token = credentials.credentials
        # Check if it's an API key format (starts with sk-)
        if token.startswith("sk-"):
            api_key_data = await verify_api_key(token)
            if api_key_data:
                return api_key_data
            # API key was provided but invalid - return error immediately
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={
                    "WWW-Authenticate": "Bearer",
                    "Retry-After": "0",  # Tell client not to retry authentication errors
                },
            )
        else:
            # Try JWT token (for admin users)
            user = verify_jwt_token(token)
            if user:
                # Verify user is active
                db = get_database()
                user_data = await db.get_user_by_id(user["user_id"])
                if user_data and user_data.get("is_active"):
                    logger.info(f"JWT token authentication successful for user {user_data['email']}")
                    return {
                        "user_id": user_data["id"],
                        "email": user_data["email"],
                        "name": user_data.get("name"),
                        "is_admin": user_data.get("is_admin", False),
                        "type": "jwt"
                    }
            # JWT token was provided but invalid
            logger.warning("Invalid JWT token provided to API endpoint")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={
                    "WWW-Authenticate": "Bearer",
                    "Retry-After": "0",
                },
            )

    # No authentication provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API key or authentication token required",
        headers={
            "WWW-Authenticate": "Bearer",
            "Retry-After": "0",  # Tell client not to retry authentication errors
        },
    )


def require_admin():
    """
    Dependency for requiring admin authentication (for management panel).
    
    Returns:
        Dependency function
    """
    async def dependency(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ):
        return await get_current_admin_user(credentials, request)
    
    return dependency


def require_api_key():
    """
    Dependency for requiring API key authentication (for service API).

    Returns:
        Dependency function
    """
    async def dependency(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ):
        return await get_current_api_user(credentials, request)

    return dependency


# Alias for verify_jwt_token (used by core/__init__.py)
verify_token = verify_jwt_token

# Alias for create_access_token (used by core/__init__.py)
create_token = create_access_token
decode_token = verify_jwt_token

# Alias for require_api_key (used by core/__init__.py)
token_required = require_api_key


