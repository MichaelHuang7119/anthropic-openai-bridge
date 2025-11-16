"""Main FastAPI application for Anthropic OpenAI Bridge"""
import os
import logging
from fastapi import FastAPI

from .config import config
from .core import ModelManager
from .api.providers import router as providers_router, set_provider_service
from .api.health import router as api_health_router, set_health_service
from .api.config import router as config_router
from .api.stats import router as stats_router
from .api.auth import router as auth_router
from .api.api_keys import router as api_keys_router
from .routes.messages import create_messages_router
from .routes.health import router as health_router
from .lifecycle import startup_event, shutdown_event
from .services.message_service import MessageService
from .services.health_service import HealthService
from .services.provider_service import ProviderService

# Configure logging
# Allow log level to be set via environment variable or default to INFO
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
# Map string level to logging constant
log_level_map = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}
logging.basicConfig(level=log_level_map.get(log_level, logging.INFO))
logger = logging.getLogger(__name__)
logger.info(f"Logging level set to: {log_level}")

# Initialize OpenTelemetry if enabled
_telemetry_enabled = os.getenv("ENABLE_TELEMETRY", "true").lower() in ("true", "1", "yes")
if _telemetry_enabled:
    try:
        from .infrastructure.telemetry import initialize_telemetry, instrument_fastapi, instrument_httpx
        initialize_telemetry(
            service_name="anthropic-openai-bridge",
            otlp_endpoint=os.getenv("OTLP_ENDPOINT"),
            enable_tracing=True,
            enable_metrics=True
        )
        instrument_httpx()
        logger.info("OpenTelemetry enabled")
    except Exception as e:
        logger.warning(f"Failed to initialize OpenTelemetry: {e}")

# Suppress verbose httpx/httpcore logging from OpenAI SDK
# This prevents logging every HTTP request, reducing noise in logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

app = FastAPI(
    title="Anthropic OpenAI Bridge",
    description="""
    Anthropic-compatible API proxy service.
    
    ## Claude Code 配置
    
    在 Claude Code 中使用本服务，需要配置以下环境变量：
    
    ```bash
    export ANTHROPIC_BASE_URL=http://localhost:5175
    export ANTHROPIC_API_KEY="any-value"
    ```
    
    然后启动 Claude Code 进行 Vibe Coding。
    
    **注意**：`ANTHROPIC_BASE_URL` 需要替换为实际的前端服务地址。
    """,
    version="1.0.0"
)

# Instrument FastAPI with OpenTelemetry if enabled
if _telemetry_enabled:
    try:
        from .infrastructure.telemetry import instrument_fastapi
        instrument_fastapi(app)
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI: {e}")

model_manager = ModelManager(config)

# Initialize services
message_service = MessageService(model_manager)
health_service = HealthService(message_service)
provider_service = ProviderService()

# Set service instances for API routes
set_health_service(health_service)
set_provider_service(provider_service)

# Register routes
app.include_router(create_messages_router(model_manager))
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(api_keys_router)
app.include_router(providers_router)
app.include_router(api_health_router)
app.include_router(config_router)
app.include_router(stats_router)


@app.on_event("startup")
async def on_startup():
    """Application startup event."""
    await startup_event()


@app.on_event("shutdown")
async def on_shutdown():
    """Application shutdown event."""
    await shutdown_event()
