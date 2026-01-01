"""Permission constants and categories for role-based access control."""
from typing import Literal
from enum import Enum


class PermissionCategory(str, Enum):
    """Permission categories for the application."""
    CHAT = "chat"
    CONVERSATIONS = "conversations"
    PREFERENCES = "preferences"
    PROVIDERS = "providers"
    API_KEYS = "api_keys"
    STATS = "stats"
    HEALTH = "health"
    CONFIG = "config"
    USERS = "users"


# Permission metadata with names and descriptions
PERMISSIONS: dict[PermissionCategory, dict] = {
    PermissionCategory.CHAT: {
        "name": "Chat Access",
        "category": "feature",
        "description": "Access to chat functionality and messaging API"
    },
    PermissionCategory.CONVERSATIONS: {
        "name": "Conversation Management",
        "category": "feature",
        "description": "Create, edit, delete conversations"
    },
    PermissionCategory.PREFERENCES: {
        "name": "User Preferences",
        "category": "feature",
        "description": "Modify personal preferences (language, theme)"
    },
    PermissionCategory.PROVIDERS: {
        "name": "Provider Management",
        "category": "admin",
        "description": "View and configure AI providers"
    },
    PermissionCategory.API_KEYS: {
        "name": "API Key Management",
        "category": "admin",
        "description": "Create and manage API keys"
    },
    PermissionCategory.STATS: {
        "name": "Statistics & Logs",
        "category": "admin",
        "description": "View usage statistics and request logs"
    },
    PermissionCategory.HEALTH: {
        "name": "Health Monitoring",
        "category": "admin",
        "description": "View provider health status"
    },
    PermissionCategory.CONFIG: {
        "name": "System Configuration",
        "category": "admin",
        "description": "Modify global system settings"
    },
    PermissionCategory.USERS: {
        "name": "User Management",
        "category": "admin",
        "description": "View and manage user accounts"
    },
}


# Default permissions for regular users (non-admin)
DEFAULT_USER_PERMISSIONS: dict[PermissionCategory, bool] = {
    PermissionCategory.CHAT: True,
    PermissionCategory.CONVERSATIONS: True,
    PermissionCategory.PREFERENCES: True,
    PermissionCategory.PROVIDERS: False,
    PermissionCategory.API_KEYS: False,
    PermissionCategory.STATS: False,
    PermissionCategory.HEALTH: False,
    PermissionCategory.CONFIG: False,
    PermissionCategory.USERS: False,
}


# Admin gets all permissions
ADMIN_PERMISSIONS: dict[PermissionCategory, bool] = {
    cat: True for cat in PermissionCategory
}
