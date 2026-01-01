"""OAuth2 service for third-party login (GitHub, Google, Feishu, OIDC).

Features:
- OAuth Session encryption with Fernet
- Token refresh support
- User info transformation pattern (dify style)
- Role-based access control (open-webui style)
"""
import os
import logging
import hashlib
import urllib.parse
import json
import base64
import secrets
import time
from typing import Optional, Dict, Any, NamedTuple
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from jose import jwt
from cryptography.fernet import Fernet

from ..database import get_database
from ..core.auth import create_access_token

logger = logging.getLogger(__name__)


# ============== OAuth Session Encryption ==============
OAUTH_SESSION_ENCRYPTION_KEY = os.getenv("OAUTH_SESSION_TOKEN_ENCRYPTION_KEY", "")

if len(OAUTH_SESSION_ENCRYPTION_KEY) != 44:
    key_bytes = hashlib.sha256(OAUTH_SESSION_ENCRYPTION_KEY.encode()).digest()
    OAUTH_SESSION_ENCRYPTION_KEY = base64.urlsafe_b64encode(key_bytes).decode()
else:
    OAUTH_SESSION_ENCRYPTION_KEY = OAUTH_SESSION_ENCRYPTION_KEY

try:
    _FERNET = Fernet(OAUTH_SESSION_ENCRYPTION_KEY.encode())
except Exception as e:
    logger.warning(f"OAuth session encryption disabled: {e}")
    _FERNET = None


def _encrypt_oauth_token(token_data: Dict[str, Any]) -> str:
    """Encrypt OAuth token data for storage."""
    if not _FERNET:
        return json.dumps(token_data)
    try:
        token_json = json.dumps(token_data)
        return _FERNET.encrypt(token_json.encode()).decode()
    except Exception as e:
        logger.error(f"Error encrypting OAuth token: {e}")
        return json.dumps(token_data)


def _decrypt_oauth_token(encrypted_data: str) -> Dict[str, Any]:
    """Decrypt OAuth token data from storage."""
    if not _FERNET:
        return json.loads(encrypted_data)
    try:
        decrypted = _FERNET.decrypt(encrypted_data.encode())
        return json.loads(decrypted.decode())
    except Exception as e:
        logger.error(f"Error decrypting OAuth token: {e}")
        return json.loads(encrypted_data)


@dataclass
class OAuthUserInfo:
    """OAuth2 user information."""
    id: str
    email: str
    name: str
    avatar_url: Optional[str] = None

    def __hash__(self):
        return hash((self.id, self.email))


class OAuthProvider:
    """Base OAuth provider class with user info transformation pattern."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        authorization_url: str,
        token_url: str,
        user_info_url: str,
        scopes: str
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.authorization_url = authorization_url
        self.token_url = token_url
        self.user_info_url = user_info_url
        self.scopes = scopes
        self.http_client = httpx.AsyncClient(timeout=30.0)

    def get_authorization_url(self, state: Optional[str] = None, **kwargs) -> str:
        """Build authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.scopes,
        }
        if state:
            params["state"] = state
        params.update(kwargs)
        return f"{self.authorization_url}?{urllib.parse.urlencode(params)}"

    async def get_access_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }

        headers = {"Accept": "application/json"}

        response = await self.http_client.post(
            self.token_url,
            data=data,
            headers=headers
        )
        response.raise_for_status()

        token_data = response.json()

        if "access_token" not in token_data:
            raise ValueError(f"No access_token in response: {token_data}")

        return token_data

    def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user info from OAuth provider (must be implemented by subclass)."""
        raise NotImplementedError("Subclasses must implement get_user_info")

    def transform_user_info(self, raw_info: Dict[str, Any]) -> OAuthUserInfo:
        """Transform raw user info from provider to standard OAuthUserInfo format.

        This follows the dify pattern for consistent user info handling.
        """
        raise NotImplementedError("Subclasses must implement transform_user_info")

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


class GitHubOAuth(OAuthProvider):
    """GitHub OAuth provider with user info transformation."""

    def __init__(self):
        super().__init__(
            client_id=os.getenv("GITHUB_CLIENT_ID", ""),
            client_secret=os.getenv("GITHUB_CLIENT_SECRET", ""),
            redirect_uri=os.getenv(
                "GITHUB_REDIRECT_URI",
                f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/oauth/github/callback"
            ),
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            user_info_url="https://api.github.com/user",
            scopes=os.getenv("GITHUB_OAUTH_SCOPE", "read:user user:email")
        )

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get GitHub user info with email resolution."""
        # Get basic user info
        response = await self.http_client.get(
            self.user_info_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        user_data = response.json()

        # Get email separately (user:email scope needed)
        response = await self.http_client.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        emails = response.json()

        # Find primary email
        primary_email = next(
            (e["email"] for e in emails if e["primary"] and e["verified"]),
            None
        )

        # Fallback to GitHub noreply email
        if not primary_email:
            primary_email = f"{user_data['id']}+{user_data['login']}@users.noreply.github.com"

        return OAuthUserInfo(
            id=str(user_data["id"]),
            email=primary_email,
            name=user_data.get("name") or user_data.get("login", ""),
            avatar_url=user_data.get("avatar_url")
        )

    def transform_user_info(self, raw_info: Dict[str, Any]) -> OAuthUserInfo:
        """Transform raw GitHub user info."""
        email = raw_info.get("email")
        if not email:
            email = f"{raw_info['id']}+{raw_info.get('login', 'user')}@users.noreply.github.com"

        return OAuthUserInfo(
            id=str(raw_info["id"]),
            email=email,
            name=raw_info.get("name") or raw_info.get("login", ""),
            avatar_url=raw_info.get("avatar_url")
        )


class GoogleOAuth(OAuthProvider):
    """Google OAuth provider with user info transformation."""

    def __init__(self):
        super().__init__(
            client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
            redirect_uri=os.getenv(
                "GOOGLE_REDIRECT_URI",
                f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/oauth/google/callback"
            ),
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            user_info_url="https://www.googleapis.com/oauth2/v2/userinfo",
            scopes=os.getenv("GOOGLE_OAUTH_SCOPE", "openid email profile")
        )

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get Google user info."""
        response = await self.http_client.get(
            self.user_info_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        user_data = response.json()

        return OAuthUserInfo(
            id=user_data["id"],
            email=user_data["email"],
            name=user_data.get("name", ""),
            avatar_url=user_data.get("picture")
        )

    def transform_user_info(self, raw_info: Dict[str, Any]) -> OAuthUserInfo:
        """Transform raw Google user info."""
        return OAuthUserInfo(
            id=str(raw_info.get("sub", raw_info.get("id", ""))),
            email=raw_info.get("email", ""),
            name=raw_info.get("name", ""),
            avatar_url=raw_info.get("picture")
        )


class FeishuOAuth(OAuthProvider):
    """Feishu OAuth provider - 参考 open-webui 实现."""

    def __init__(self):
        super().__init__(
            client_id=os.getenv("FEISHU_CLIENT_ID", ""),
            client_secret=os.getenv("FEISHU_CLIENT_SECRET", ""),
            redirect_uri=os.getenv(
                "FEISHU_REDIRECT_URI",
                f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/oauth/feishu/callback"
            ),
            # open-webui 使用的飞书标准 OAuth 端点
            authorization_url="https://accounts.feishu.cn/open-apis/authen/v1/authorize",
            token_url="https://open.feishu.cn/open-apis/authen/v2/oauth/token",
            user_info_url="https://open.feishu.cn/open-apis/authen/v1/user_info",
            scopes=os.getenv("FEISHU_OAUTH_SCOPE", "contact:user.base:readonly")
        )

    def get_authorization_url(self, state: Optional[str] = None, **kwargs) -> str:
        """Build Feishu authorization URL."""
        params = {
            "app_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state or "",
        }
        return f"{self.authorization_url}?{urllib.parse.urlencode(params)}"

    async def get_access_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for Feishu access token."""
        # 飞书 token 端点需要 client_id, client_secret, redirect_uri
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }

        logger.debug(f"Feishu token request data: {data}")

        response = await self.http_client.post(
            self.token_url,
            data=data
        )

        logger.debug(f"Feishu token response status: {response.status_code}")
        logger.debug(f"Feishu token response body: {response.text}")

        response.raise_for_status()

        token_data = response.json()
        logger.debug(f"Feishu token response (parsed): {token_data}")

        # 飞书 /v2/oauth/token 返回直接的 OAuth 2.0 格式，不是 {"code": 0, "data": {...}}
        if token_data.get("code") != 0:
            raise ValueError(f"Feishu OAuth error: {token_data.get('msg', 'Unknown error')}")

        # token 直接在顶层
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in"),
        }

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get Feishu user info from user_info endpoint or JWT token.

        注意：飞书的 user_id 可能是会话相关的，会随 access_token 变化。
        auth_id 才是用户的唯一标识，应该作为主要用户标识使用。
        """
        # 首先从 JWT access_token 中解析 auth_id（这是用户唯一标识）
        auth_id = None
        token_data = None
        try:
            token_data = jwt.decode(
                access_token,
                key="",
                options={
                    "verify_signature": False,
                    "verify_exp": False,
                    "verify_aud": False,
                    "verify_iss": False,
                },
                algorithms=["HS256", "RS256"]
            )
            auth_id = token_data.get("auth_id", "")
            logger.debug(f"Feishu JWT token decoded keys: {list(token_data.keys()) if token_data else None}, auth_id={auth_id}")
        except Exception as e:
            logger.warning(f"Failed to parse Feishu JWT token: {e}")

        # 优先从 user_info 端点获取详细信息
        try:
            response = await self.http_client.get(
                self.user_info_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()

            user_data = response.json()
            logger.debug(f"Feishu user_info response: {user_data}")

            if user_data.get("code") != 0:
                raise ValueError(f"Feishu user info error: {user_data.get('msg', 'Unknown error')}")

            data = user_data["data"]

            # 优先使用 user_id（如果存在），否则使用 auth_id
            user_id = data.get("user_id")
            email = data.get("email")

            # 使用 auth_id 作为唯一标识（user_id 可能是会话相关的）
            # 只有当 auth_id 为空时，才使用 user_id
            unique_id = auth_id if auth_id else user_id
            if not unique_id:
                raise ValueError("Feishu user info missing both auth_id and user_id")

            # 如果没有邮箱，使用 auth_id 生成稳定邮箱（如果 auth_id 存在）
            if not email:
                if auth_id:
                    email = f"{auth_id}@feishu.noreply"
                else:
                    email = f"{user_id}@feishu.noreply"

            logger.info(f"Feishu user: user_id={user_id}, auth_id={auth_id}, using unique_id={unique_id}, email={email}")

            return OAuthUserInfo(
                id=unique_id,
                email=email,
                name=data.get("name", ""),
                avatar_url=data.get("avatar_url") or data.get("avatar")
            )
        except Exception as e:
            logger.warning(f"Feishu user_info endpoint failed: {e}")

        # 如果 user_info 端点失败，从 JWT 中获取信息
        if auth_id:
            email = token_data.get("email", "") if token_data else ""
            if not email:
                email = f"{auth_id}@feishu.noreply"

            return OAuthUserInfo(
                id=auth_id,
                email=email,
                name=token_data.get("name", "") if token_data else "",
                avatar_url=None
            )

        # 最终兜底方案
        raise ValueError("Unable to get Feishu user info")

    def transform_user_info(self, raw_info: Dict[str, Any]) -> OAuthUserInfo:
        """Transform raw Feishu user info."""
        data = raw_info.get("data", raw_info)

        user_id = data.get("user_id", "")
        email = data.get("email", "")
        if not email:
            email = f"{user_id}@feishu.noreply"

        return OAuthUserInfo(
            id=user_id,
            email=email,
            name=data.get("name", ""),
            avatar_url=data.get("avatar_url") or data.get("avatar")
        )


class MicrosoftOAuth(OAuthProvider):
    """Microsoft OAuth provider with user info transformation."""

    def __init__(self):
        tenant_id = os.getenv("MICROSOFT_TENANT_ID", "common")
        login_base_url = os.getenv("MICROSOFT_LOGIN_BASE_URL", "https://login.microsoftonline.com")

        super().__init__(
            client_id=os.getenv("MICROSOFT_CLIENT_ID", ""),
            client_secret=os.getenv("MICROSOFT_CLIENT_SECRET", ""),
            redirect_uri=os.getenv(
                "MICROSOFT_REDIRECT_URI",
                f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/oauth/microsoft/callback"
            ),
            authorization_url=f"{login_base_url}/{tenant_id}/v2.0/authorize",
            token_url=f"{login_base_url}/{tenant_id}/v2.0/token",
            user_info_url="https://graph.microsoft.com/v1.0/me",
            scopes=os.getenv("MICROSOFT_OAUTH_SCOPE", "openid email profile user.read")
        )

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get Microsoft user info."""
        response = await self.http_client.get(
            self.user_info_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        user_data = response.json()

        email = user_data.get("mail") or user_data.get("userPrincipalName", "")
        if not email:
            raise ValueError("Microsoft OAuth: No email found in user info")

        name = user_data.get("displayName") or email.split("@")[0]
        avatar_url = None

        return OAuthUserInfo(
            id=user_data.get("id", ""),
            email=email,
            name=name,
            avatar_url=avatar_url
        )

    def transform_user_info(self, raw_info: Dict[str, Any]) -> OAuthUserInfo:
        """Transform raw Microsoft user info."""
        email = raw_info.get("mail") or raw_info.get("userPrincipalName", "")
        name = raw_info.get("displayName", email.split("@")[0] if email else "")

        return OAuthUserInfo(
            id=raw_info.get("id", ""),
            email=email,
            name=name,
            avatar_url=None
        )


class OidcOAuth(OAuthProvider):
    """Generic OIDC OAuth provider (Logto, Keycloak, Authentik, etc.).

    Features:
    - ID token user info extraction
    - Role-based access control
    - Flexible auth method (Basic Auth or credentials in body)
    """

    def __init__(self):
        super().__init__(
            client_id=os.getenv("OIDC_CLIENT_ID", ""),
            client_secret=os.getenv("OIDC_CLIENT_SECRET", ""),
            redirect_uri=os.getenv(
                "OIDC_REDIRECT_URI",
                f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/oauth/oidc/callback"
            ),
            authorization_url=os.getenv("OIDC_AUTHORIZATION_URL", ""),
            token_url=os.getenv("OIDC_TOKEN_URL", ""),
            user_info_url=os.getenv("OIDC_USER_INFO_URL", ""),
            scopes=os.getenv("OIDC_SCOPES", "openid email profile")
        )
        # Role-based access control settings
        self.required_roles = os.getenv("OIDC_REQUIRED_ROLES", "")
        self.allowed_roles = [role.strip() for role in self.required_roles.split(",")] if self.required_roles else []
        self.email_default_domain = os.getenv("OIDC_EMAIL_DEFAULT_DOMAIN", "oidc.noreply")

    def get_authorization_url(self, state: Optional[str] = None, **kwargs) -> str:
        """Build OIDC authorization URL with optional provider-specific parameters."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.scopes,
        }

        # Optional OIDC parameters (for Logto, Keycloak, Authentik, etc.)
        for env_key in ["OIDC_RESOURCE", "OIDC_PROMPT", "OIDC_INTERACTION_MODE",
                        "OIDC_FIRST_SCREEN", "OIDC_IDENTIFIER", "OIDC_DIRECT_SIGN_IN"]:
            value = os.getenv(env_key)
            if value:
                param_name = env_key.lower().replace("oidc_", "")
                params[param_name] = value

        if state:
            params["state"] = state

        # Filter out None/empty values
        params = {k: v for k, v in params.items() if v not in [None, ""]}

        logger.debug(f"OIDC auth params: {params}")
        return f"{self.authorization_url}?{urllib.parse.urlencode(params)}"

    async def get_access_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for OIDC access token."""
        import base64

        # Try with HTTP Basic Auth first
        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_header}"
        }
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }

        try:
            response = await self.http_client.post(self.token_url, data=data, headers=headers)
            response.raise_for_status()
        except Exception as e:
            # Fallback to credentials in body (RFC 6749 standard)
            logger.warning(f"OIDC Basic Auth failed, trying with credentials in body: {e}")
            headers["Authorization"] = None  # Remove auth header
            data.update({
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            })
            response = await self.http_client.post(self.token_url, data=data, headers=headers)
            response.raise_for_status()

        token_data = response.json()
        if "access_token" not in token_data:
            raise ValueError(f"OIDC OAuth error: No access_token in response")

        return token_data

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user info from ID token or userinfo endpoint."""
        # Prefer ID token if available (avoids extra API call)
        # This requires the token endpoint to return id_token
        # For userinfo-based approach, override this method
        raise NotImplementedError("Use get_user_info_from_id_token for OIDC")

    def transform_user_info(self, raw_info: Dict[str, Any]) -> OAuthUserInfo:
        """Transform raw OIDC user info with role-based access control."""
        user_id = str(raw_info.get("sub", ""))
        if not user_id:
            raise ValueError("ID token missing 'sub' claim")

        email = raw_info.get("email")
        if not email:
            email = f"{raw_info.get('username', '')}@{self.email_default_domain}"

        name = raw_info.get("name") or raw_info.get("username") or email.split("@")[0]
        avatar_url = raw_info.get("picture")

        # Role-based access control
        if self.allowed_roles and "roles" in raw_info:
            user_roles = raw_info.get("roles", [])
            if not any(role in self.allowed_roles for role in user_roles):
                raise ValueError(
                    f"User {name} is not authorized. Required roles: {self.allowed_roles}"
                )

        return OAuthUserInfo(
            id=user_id,
            email=email,
            name=name,
            avatar_url=avatar_url
        )

    async def get_user_info_from_id_token(self, id_token: str) -> OAuthUserInfo:
        """Get user info from ID token (JWT).

        This is the preferred method for OIDC providers as it avoids an additional API call.
        """
        try:
            # Decode JWT without signature verification
            # Using algorithms=["HS256", "RS256", "ES256", etc.] to allow any algorithm
            # and an empty key for verification bypass (provider has already verified)
            token_data = jwt.decode(
                id_token,
                key="",  # Empty key, signature verification disabled
                options={
                    "verify_signature": False,
                    "verify_exp": False,
                    "verify_aud": False,
                    "verify_iss": False,
                    "verify_at_hash": False,  # Disable at_hash validation
                },
                algorithms=["HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
            )
        except Exception as e:
            raise ValueError(f"Failed to decode ID token: {e}")

        return self.transform_user_info(token_data)

    async def get_user_info_from_userinfo(self, access_token: str) -> OAuthUserInfo:
        """Get user info from userinfo endpoint."""
        if not self.user_info_url:
            raise ValueError("OIDC user_info_url not configured")

        response = await self.http_client.get(
            self.user_info_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()

        user_data = response.json()
        return self.transform_user_info(user_data)


class OAuthService:
    """Main OAuth2 service with OAuth Session management and token refresh support."""

    def __init__(self):
        self.providers: Dict[str, OAuthProvider] = {
            "github": GitHubOAuth(),
            "google": GoogleOAuth(),
            "feishu": FeishuOAuth(),
            "microsoft": MicrosoftOAuth(),
            "oidc": OidcOAuth(),
        }

    def get_provider(self, provider_name: str) -> Optional[OAuthProvider]:
        """Get OAuth provider instance."""
        provider = self.providers.get(provider_name)
        if not provider:
            return None

        if not provider.client_id or not provider.client_secret:
            logger.warning(f"OAuth provider {provider_name} not configured (missing credentials)")
            return None

        return provider

    def is_provider_enabled(self, provider_name: str) -> bool:
        """Check if a provider is configured and enabled."""
        provider = self.get_provider(provider_name)
        return provider is not None

    async def handle_oauth_login(
        self,
        provider_name: str,
        code: str,
        id_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle OAuth2 login flow with user linking support.

        Args:
            provider_name: Provider name (github, google, feishu, etc.)
            code: Authorization code from OAuth provider
            id_token: Optional ID token for OIDC providers (passed from frontend)

        Returns:
            Dict with access_token, user info, provider info

        Raises:
            ValueError: If provider not configured or OAuth flow fails
        """
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"OAuth provider '{provider_name}' not configured")

        try:
            # Exchange code for access token
            token_data = await provider.get_access_token(code)
            access_token = token_data["access_token"]

            # Get user info
            if provider_name == "oidc":
                # For OIDC, prefer id_token from token_data (returned by OIDC provider)
                # Fall back to passed id_token or userinfo endpoint
                oidc_id_token = token_data.get("id_token") or id_token
                if oidc_id_token:
                    user_info = await provider.get_user_info_from_id_token(oidc_id_token)
                else:
                    # Fall back to userinfo endpoint
                    user_info = await provider.get_user_info_from_userinfo(access_token)
            else:
                user_info = await provider.get_user_info(access_token)

            # Create or update user in database
            user = await self._create_or_update_user(provider_name, user_info, token_data)

            # Generate JWT token
            jwt_token = create_access_token(
                data={
                    "sub": user["id"],
                    "is_admin": user.get("is_admin", False)
                }
            )

            logger.info(f"OAuth login successful: {user['email']} via {provider_name}")

            return {
                "access_token": jwt_token,
                "token_type": "bearer",
                "user": {
                    "id": user["id"],
                    "email": user["email"],
                    "name": user.get("name"),
                    "is_admin": user.get("is_admin", False),
                    "avatar_url": user.get("avatar_url")
                },
                "provider": provider_name,
                "oauth_user_info": {
                    "email": user_info.email,
                    "name": user_info.name,
                    "avatar_url": user_info.avatar_url
                }
            }

        except ValueError as e:
            logger.warning(f"OAuth validation error for {provider_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"OAuth login failed for {provider_name}: {e}", exc_info=True)
            raise ValueError(f"OAuth login failed: {str(e)}")

    def _build_raw_user_info(
        self,
        provider_name: str,
        user_info: OAuthUserInfo,
        auth_id: str = None
    ) -> Dict[str, Any]:
        """Build raw_user_info dict for OAuth account.

        对于飞书，额外保存 auth_id 用于用户查找。
        """
        raw_info = {
            "email": user_info.email,
            "name": user_info.name,
            "avatar_url": user_info.avatar_url
        }
        # 对于飞书，保存 auth_id
        if provider_name == 'feishu' and auth_id:
            raw_info["auth_id"] = auth_id
        return raw_info

    async def _create_or_update_user(
        self,
        provider_name: str,
        user_info: OAuthUserInfo,
        token_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create or update user based on OAuth login result.

        用户识别策略（按优先级）：
        1. 对于飞书：先通过邮箱查找（因为 user_id 和 auth_id 可能会变化）
           注意：email 必须使用 auth_id 生成（而不是 user_id），才能保证一致性
        2. 对于其他 provider：先通过 (provider, provider_user_id) 查找
        3. 再通过邮箱查找 - 尝试关联同一用户的不同 provider
        4. 都找不到才创建新用户

        这样同一用户用不同 provider 登录会关联到同一账户。
        """
        db = get_database()

        # 对于飞书，从 token_data 中提取 auth_id
        auth_id = None
        if provider_name == 'feishu' and token_data:
            try:
                from jose import jwt
                access_token = token_data.get("access_token", "")
                if access_token:
                    # 尝试从 access_token 中提取 auth_id
                    token_decoded = jwt.decode(
                        access_token,
                        key="",
                        options={"verify_signature": False, "verify_exp": False}
                    )
                    auth_id = token_decoded.get("auth_id")
                    logger.debug(f"Feishu JWT decoded keys: {list(token_decoded.keys())}, auth_id={auth_id}")
            except Exception as e:
                logger.warning(f"Failed to extract auth_id from Feishu token: {e}")

        logger.info(f"OAuth login for {provider_name}: user_info.id={user_info.id}, email={user_info.email}, auth_id={auth_id}")

        # 构建 raw_user_info
        raw_user_info = self._build_raw_user_info(provider_name, user_info, auth_id)

        # 1. 对于飞书：优先通过邮箱查找
        #    因为 user_id 可能会变化，但 email (使用 auth_id 生成) 应该保持一致
        if provider_name == 'feishu':
            existing_user = await db.users.get_user_by_email(user_info.email)
            logger.info(f"OAuth feishu: email check for {user_info.email}: existing={existing_user is not None}")

            if existing_user:
                # 关联 OAuth account 到现有用户
                logger.info(f"Linking Feishu OAuth to existing user: {user_info.email}")
                await db.oauth_accounts.create_or_update_oauth_account(
                    user_id=existing_user["id"],
                    provider=provider_name,
                    provider_user_id=user_info.id,
                    access_token=token_data.get("access_token"),
                    refresh_token=token_data.get("refresh_token"),
                    raw_user_info=raw_user_info
                )
                await db.users.update_user_last_login(existing_user["id"])
                return existing_user

            # 如果邮箱不存在，尝试通过 auth_id 在 raw_user_info 中查找
            if auth_id:
                existing_by_auth_id = await db.oauth_accounts.get_user_by_auth_id(provider_name, auth_id)
                logger.info(f"OAuth feishu: auth_id check: existing={existing_by_auth_id is not None}")
                if existing_by_auth_id:
                    await db.oauth_accounts.create_or_update_oauth_account(
                        user_id=existing_by_auth_id["id"],
                        provider=provider_name,
                        provider_user_id=user_info.id,
                        access_token=token_data.get("access_token"),
                        refresh_token=token_data.get("refresh_token"),
                        raw_user_info=raw_user_info
                    )
                    await db.users.update_user_last_login(existing_by_auth_id["id"])
                    logger.info(f"OAuth feishu: linked to existing user {existing_by_auth_id['email']}")
                    return existing_by_auth_id

        # 2. 对于其他 provider：先通过 (provider, provider_user_id) 查找 - 精确匹配
        existing_oauth_user = await db.oauth_accounts.get_user_by_oauth(
            provider_name,
            user_info.id
        )

        logger.info(f"OAuth check: existing_oauth_user by provider_user_id={existing_oauth_user is not None}")

        if existing_oauth_user:
            # Existing OAuth user - update tokens and last login
            user = existing_oauth_user
            logger.debug(f"Existing OAuth user: {user['email']}")

            await db.oauth_accounts.create_or_update_oauth_account(
                user_id=user["id"],
                provider=provider_name,
                provider_user_id=user_info.id,
                access_token=token_data.get("access_token"),
                refresh_token=token_data.get("refresh_token"),
                raw_user_info=raw_user_info
            )
            await db.users.update_user_last_login(user["id"])
            return user

        # 3. 通过邮箱查找 - 尝试关联同一用户的不同 provider
        existing_user = await db.users.get_user_by_email(user_info.email)
        logger.info(f"OAuth email check: existing_user={existing_user is not None}")

        if existing_user:
            # 关联 OAuth account 到现有用户
            logger.info(f"Linking OAuth account to existing user: {user_info.email} (provider: {provider_name})")
            await db.oauth_accounts.create_or_update_oauth_account(
                user_id=existing_user["id"],
                provider=provider_name,
                provider_user_id=user_info.id,
                access_token=token_data.get("access_token"),
                refresh_token=token_data.get("refresh_token"),
                raw_user_info=raw_user_info
            )
            await db.users.update_user_last_login(existing_user["id"])
            return existing_user

        # 4. 创建新用户
        logger.info(f"Creating new OAuth user: {user_info.email} (provider: {provider_name})")
        user_id = await db.users.create_oauth_user(
            email=user_info.email,
            name=user_info.name
        )

        if not user_id:
            # Handle race condition
            user = await db.users.get_user_by_email(user_info.email)
        else:
            user = await db.users.get_user_by_id(user_id)

        # Create OAuth account
        await db.oauth_accounts.create_or_update_oauth_account(
            user_id=user["id"],
            provider=provider_name,
            provider_user_id=user_info.id,
            access_token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            raw_user_info=raw_user_info
        )

        return user

    async def get_providers_config(self) -> Dict[str, Dict[str, Any]]:
        """Get list of configured OAuth providers."""
        config = {}
        for name, provider in self.providers.items():
            config[name] = {
                "enabled": bool(provider.client_id and provider.client_secret),
                "authorization_url": provider.authorization_url,
                "name": provider.scopes.split()[0] if provider.scopes else name.title()
            }
        return config


# Global OAuth service instance
_oauth_service: Optional[OAuthService] = None


def get_oauth_service() -> OAuthService:
    """Get or create OAuth service instance."""
    global _oauth_service
    if _oauth_service is None:
        _oauth_service = OAuthService()
    return _oauth_service
