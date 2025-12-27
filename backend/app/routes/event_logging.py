"""Event logging routes."""
import logging
import os
from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["event_logging"])

# Environment variable to enable verbose event logging (default: false)
VERBOSE_EVENT_LOGGING = os.environ.get("VERBOSE_EVENT_LOGGING", "false").lower() in ("true", "1", "yes", "on")


@router.post("/event_logging/batch")
async def batch_event_logging(request: Request):
    """Handle Claude Code event logging batch endpoint.

    This endpoint receives event logs from Claude Code CLI for analytics.
    Currently, we just accept and log these events without storing them.
    """
    try:
        body = await request.json()

        # Only log event details if verbose logging is enabled
        if VERBOSE_EVENT_LOGGING:
            logger.info(
                f"Received event logging batch: {body}"
            )
        else:
            # Just log that we received an event batch (for monitoring without the verbose details)
            logger.debug(
                "Received event logging batch (details omitted - set VERBOSE_EVENT_LOGGING=true to see them)"
            )

        # For now, just return success without storing the events
        # In the future, this could be used for analytics or monitoring
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error handling event logging: {e}")
        # Still return 200 to avoid breaking Claude Code
        return {"status": "ok"}
