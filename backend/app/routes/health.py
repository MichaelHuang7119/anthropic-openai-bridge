"""Health check and root routes."""
from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/favicon.ico")
async def favicon():
    """Favicon endpoint - returns 204 No Content to prevent 404 errors."""
    return Response(status_code=204)


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Anthropic OpenAI Bridge",
        "version": "1.0.0",
        "description": "Anthropic-compatible API proxy service",
        "claude_code_config": {
            "instructions": "在 Claude Code 中配置以下环境变量：",
            "environment_variables": {
                "ANTHROPIC_BASE_URL": "http://localhost:5175",
                "ANTHROPIC_API_KEY": "any-value"
            },
            "note": "ANTHROPIC_BASE_URL 需要替换为实际的前端服务地址"
        },
        "endpoints": [
            "/v1/messages",
            "/v1/messages/count_tokens",
            "/health",
            "/api/providers",
            "/api/health",
            "/api/config"
        ]
    }



