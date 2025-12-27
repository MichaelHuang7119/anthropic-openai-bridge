"""Application constants and configuration values."""
# API version
API_VERSION = "v1"

# Message limits
MAX_MESSAGE_LENGTH = 100000
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 1.0

# Supported roles
SUPPORTED_ROLES = ["user", "assistant", "system"]

# Image size limits (width x height)
IMAGE_SIZE_LIMITS = {
    "min_width": 16,
    "min_height": 16,
    "max_width": 2048,
    "max_height": 2048,
    "max_pixels": 2048 * 2048,
}

# Token estimation constants
CHARS_PER_TOKEN = 4
TOKENS_PER_IMAGE = 85
IMAGE_TOKEN_EQUIVALENT = TOKENS_PER_IMAGE * CHARS_PER_TOKEN  # 340
MESSAGE_OVERHEAD = 10

# Cost estimation (per token)
COST_PER_1K_INPUT_TOKENS = 0.01
COST_PER_1K_OUTPUT_TOKENS = 0.03
COST_PER_INPUT_TOKEN = COST_PER_1K_INPUT_TOKENS / 1000  # 0.00001
COST_PER_OUTPUT_TOKEN = COST_PER_1K_OUTPUT_TOKENS / 1000  # 0.00003

# Color codes for logging (ANSI escape codes)
COLOR_CYAN = '\033[96m'
COLOR_GREEN = '\033[92m'
COLOR_YELLOW = '\033[93m'
COLOR_BLUE = '\033[94m'
COLOR_MAGENTA = '\033[95m'
COLOR_WHITE = '\033[97m'
COLOR_RED = '\033[91m'
COLOR_RESET = '\033[0m'

# Model rotation constants
MAX_MODEL_ATTEMPTS = 10

# HTTP client configuration (optimized for 10k QPS)
DEFAULT_MAX_KEEPALIVE_CONNECTIONS = 50
DEFAULT_MAX_CONNECTIONS = 200
DEFAULT_KEEPALIVE_EXPIRY = 60

# Retry configuration defaults
DEFAULT_INITIAL_DELAY = 1.0
DEFAULT_MAX_DELAY = 60.0
DEFAULT_EXPONENTIAL_BASE = 2.0

# SSE event types
SSE_EVENT_MESSAGE_START = "message_start"
SSE_EVENT_MESSAGE_DELTA = "message_delta"
SSE_EVENT_MESSAGE_STOP = "message_stop"
SSE_EVENT_CONTENT_BLOCK_START = "content_block_start"
SSE_EVENT_CONTENT_BLOCK_DELTA = "content_block_delta"
SSE_EVENT_CONTENT_BLOCK_STOP = "content_block_stop"
SSE_EVENT_PING = "ping"
SSE_EVENT_ERROR = "error"

# Error types
ERROR_TYPE_RATE_LIMIT = "rate_limit_error"
ERROR_TYPE_CONNECTION_TIMEOUT = "connection_timeout"
ERROR_TYPE_READ_TIMEOUT = "read_timeout"
ERROR_TYPE_CONNECTION_ERROR = "connection_error"
ERROR_TYPE_TIMEOUT_ERROR = "timeout_error"
ERROR_TYPE_API_ERROR = "api_error"
ERROR_TYPE_INTERNAL_ERROR = "internal_error"

