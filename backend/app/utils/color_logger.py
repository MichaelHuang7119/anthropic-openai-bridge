"""Color logging utilities for better log readability."""
import logging
import sys
import re
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',     # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
        'BOLD': '\033[1m',        # Bold
        'DIM': '\033[2m',         # Dim
    }
    
    # Highlight colors for specific fields
    HIGHLIGHT_COLORS = {
        'url': '\033[94m',        # Bright Blue
        'model': '\033[93m',      # Bright Yellow
        'provider': '\033[96m',   # Bright Cyan
        'status': '\033[92m',     # Bright Green (for success)
        'error': '\033[91m',      # Bright Red (for errors)
    }
    
    def __init__(self, use_colors: bool = True):
        """Initialize the colored formatter.
        
        Args:
            use_colors: Whether to use colors. Auto-detects if output is a TTY.
        """
        super().__init__()
        # Auto-detect if we should use colors (only if output is a TTY)
        if use_colors is None:
            use_colors = sys.stdout.isatty() and sys.stderr.isatty()
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors."""
        # Get the base formatted message
        log_color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET'] if self.use_colors else ''
        
        # Format the message with level color
        if self.use_colors:
            record.levelname = f"{log_color}{record.levelname}{reset}"
            record.name = f"{self.COLORS['DIM']}{record.name}{reset}"
        
        # Format the message itself
        message = super().format(record)
        
        # Restore original levelname for next log
        if self.use_colors:
            record.levelname = logging.getLevelName(record.levelno)
        
        return message


def highlight_field(text: str, field_name: str, value: str, use_colors: bool = True) -> str:
    """Highlight a specific field in a log message.
    
    Args:
        text: The log message text
        field_name: The name of the field to highlight (e.g., 'url', 'model')
        value: The value to highlight
        use_colors: Whether to use colors
    
    Returns:
        The text with the field highlighted
    """
    if not use_colors or not value:
        return text
    
    color = ColoredFormatter.HIGHLIGHT_COLORS.get(field_name.lower(), '')
    reset = ColoredFormatter.COLORS['RESET'] if use_colors else ''
    bold = ColoredFormatter.COLORS['BOLD'] if use_colors else ''
    
    if color:
        # Escape special regex characters in value
        escaped_value = re.escape(value)
        
        # Pattern 1: url=https://..., model=ModelName (most common format)
        pattern1 = re.compile(rf'\b{re.escape(field_name)}=({escaped_value})', re.IGNORECASE)
        if pattern1.search(text):
            text = pattern1.sub(rf'{field_name}={bold}{color}\1{reset}', text)
            return text
        
        # Pattern 2: url: https://..., model: ModelName
        pattern2 = re.compile(rf'\b{re.escape(field_name)}:\s+({escaped_value})', re.IGNORECASE)
        if pattern2.search(text):
            text = pattern2.sub(rf'{field_name}: {bold}{color}\1{reset}', text)
            return text
        
        # Pattern 3: "url": "https://...", "model": "ModelName"
        pattern3 = re.compile(rf'"{re.escape(field_name)}":\s*"({escaped_value})"', re.IGNORECASE)
        if pattern3.search(text):
            text = pattern3.sub(rf'"{field_name}": "{bold}{color}\1{reset}"', text)
            return text
    
    return text


def format_log_message(
    base_message: str,
    url: Optional[str] = None,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    use_colors: bool = True
) -> str:
    """Format a log message with highlighted fields.
    
    Args:
        base_message: The base log message
        url: URL to highlight
        model: Model name to highlight
        provider: Provider name to highlight
        use_colors: Whether to use colors
    
    Returns:
        Formatted message with highlighted fields
    """
    message = base_message
    
    # Check if output is a TTY for auto-detection
    if use_colors is None:
        use_colors = sys.stdout.isatty() and sys.stderr.isatty()
    
    if use_colors:
        # Highlight URL
        if url:
            message = highlight_field(message, 'url', url, use_colors)
        
        # Highlight model
        if model:
            message = highlight_field(message, 'model', model, use_colors)
        
        # Highlight provider
        if provider:
            message = highlight_field(message, 'provider', provider, use_colors)
    
    return message


def setup_colored_logging(level: int = logging.INFO, use_colors: Optional[bool] = None):
    """Set up colored logging for the application.
    
    Args:
        level: Logging level
        use_colors: Whether to use colors. Auto-detects if None.
    """
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Create colored formatter
    formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        use_colors=use_colors
    )
    
    console_handler.setFormatter(formatter)
    
    # Get root logger and configure it
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = []  # Clear existing handlers
    root_logger.addHandler(console_handler)
    
    return root_logger

