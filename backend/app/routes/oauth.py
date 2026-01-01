"""OAuth2 authentication API endpoints - Optimized Open-WebUI Pattern.

Features:
- Simplified state management for CSRF protection
- Better error handling with user-friendly messages
- Support for both GET and POST callback methods
- Consistent redirect URLs after login
"""
import os
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
import logging
import urllib.parse

from ..services.oauth_service import get_oauth_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/oauth")

# Get frontend URL from environment, with fallback
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


def _build_error_url(request: Request, error: str, error_description: str = None) -> str:
    """Build login error redirect URL."""
    params = {"error": error}
    if error_description:
        params["error_description"] = error_description
    return f"{FRONTEND_URL}/login?{urllib.parse.urlencode(params)}"


def _build_success_url(request: Request, token: str = None) -> str:
    """Build login success redirect URL."""
    if token:
        return f"{FRONTEND_URL}/auth?token={urllib.parse.quote(token)}"
    return f"{FRONTEND_URL}/auth"


@router.get("/{provider}/login")
async def oauth_provider_login(provider: str, request: Request):
    """Initiate OAuth2 login - redirect to provider authorization page.

    This endpoint generates the authorization URL and redirects the user
    to the OAuth provider's login page.
    """
    oauth_service = get_oauth_service()

    provider_obj = oauth_service.get_provider(provider)
    if not provider_obj:
        logger.warning(f"OAuth provider '{provider}' not configured")
        return RedirectResponse(url=_build_error_url(request, "provider_not_configured"))

    try:
        logger.info(f"Initiating OAuth login for provider: {provider}")

        # Generate authorization URL with state for CSRF protection
        authorization_url = provider_obj.get_authorization_url()

        logger.debug(f"Authorization URL generated for {provider}")

        # Redirect directly to the authorization URL
        return RedirectResponse(url=authorization_url)

    except Exception as e:
        logger.error(f"OAuth login initiation failed for {provider}: {e}", exc_info=True)
        return RedirectResponse(url=_build_error_url(request, "login_failed", str(e)))


@router.get("/{provider}/callback")
async def oauth_provider_callback(provider: str, request: Request):
    """Handle OAuth2 callback (GET request from OAuth provider).

    Processes the authorization code and returns JWT token.
    On success, redirects to frontend with token.
    On error, redirects to login page with error message.
    """
    oauth_service = get_oauth_service()

    # Extract parameters from URL
    query_params = request.query_params
    code = query_params.get("code")
    error = query_params.get("error")
    error_description = query_params.get("error_description")

    # Handle OAuth errors
    if error:
        logger.warning(f"OAuth error for {provider}: {error} - {error_description}")
        return RedirectResponse(
            url=_build_error_url(request, error, error_description or "User cancelled authorization")
        )

    if not code:
        logger.error(f"No authorization code in OAuth callback for {provider}")
        return RedirectResponse(url=_build_error_url(request, "missing_code"))

    try:
        logger.info(f"Processing OAuth callback for provider: {provider}")

        # Process OAuth login
        result = await oauth_service.handle_oauth_login(provider_name=provider, code=code)

        logger.info(f"OAuth login successful: {result['user']['email']}")

        # Redirect to frontend with token
        return RedirectResponse(url=_build_success_url(request, result["access_token"]))

    except ValueError as e:
        logger.warning(f"OAuth validation error for {provider}: {e}")
        return RedirectResponse(url=_build_error_url(request, "validation_failed", str(e)))
    except Exception as e:
        logger.error(f"OAuth callback failed for {provider}: {e}", exc_info=True)
        return RedirectResponse(url=_build_error_url(request, "callback_failed", str(e)[:200]))


@router.post("/{provider}/callback")
async def oauth_provider_callback_post(provider: str, request: Request):
    """Handle OAuth2 callback (POST request from frontend callback page).

    This endpoint is used when the frontend handles the OAuth callback
    and sends the authorization code to the backend for processing.
    """
    oauth_service = get_oauth_service()

    try:
        body = await request.json()
        code = body.get("code")
        id_token = body.get("id_token")  # For OIDC providers

        if not code:
            return JSONResponse(
                status_code=400,
                content={"error": "missing_code", "message": "No authorization code received"}
            )

        # Process OAuth login
        result = await oauth_service.handle_oauth_login(
            provider_name=provider,
            code=code,
            id_token=id_token
        )

        logger.info(f"OAuth login successful via POST: {result['user']['email']}")

        # Return JWT token as JSON
        return JSONResponse(content={
            "access_token": result["access_token"],
            "token_type": "bearer",
            "user": result["user"],
            "provider": provider
        })

    except ValueError as e:
        logger.warning(f"OAuth validation error for {provider}: {e}")
        return JSONResponse(
            status_code=400,
            content={"error": "validation_failed", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"OAuth callback POST failed for {provider}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "callback_failed", "message": str(e)[:200]}
        )


@router.get("/providers")
async def list_providers():
    """Get list of configured OAuth providers."""
    try:
        oauth_service = get_oauth_service()
        config = await oauth_service.get_providers_config()
        return {"providers": config}
    except Exception as e:
        logger.error(f"Error listing OAuth providers: {e}", exc_info=True)
        return {"providers": {}}


@router.get("/{provider}/config")
async def get_provider_config(provider: str):
    """Get configuration for a specific OAuth provider."""
    oauth_service = get_oauth_service()
    provider_obj = oauth_service.get_provider(provider)

    if not provider_obj:
        return JSONResponse(
            status_code=404,
            content={"error": "provider_not_found", "message": f"Provider '{provider}' not found"}
        )

    return {
        "provider": provider,
        "enabled": oauth_service.is_provider_enabled(provider),
        "authorization_url": provider_obj.authorization_url,
        "scopes": provider_obj.scopes
    }
