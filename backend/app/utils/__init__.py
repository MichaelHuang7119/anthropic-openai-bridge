"""Utility modules for the application."""
from .response import openai_response_to_dict
from .error_handler import (
    create_error_response,
    handle_openai_exception,
    create_retry_notification
)
from .color_logger import (
    ColoredFormatter,
    highlight_field,
    format_log_message,
    setup_colored_logging
)

__all__ = [
    'openai_response_to_dict',
    'create_error_response',
    'handle_openai_exception',
    'create_retry_notification',
    'ColoredFormatter',
    'highlight_field',
    'format_log_message',
    'setup_colored_logging',
]
