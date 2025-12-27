"""
Security utilities for API key management and input validation.
Provides encryption, validation, and security best practices.
"""
import os
import re
import json
import logging
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet
from pathlib import Path
import base64

logger = logging.getLogger(__name__)

# Encryption key for sensitive data
_ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
_cipher: Optional[Fernet] = None


def init_security():
    """Initialize security system."""
    global _cipher, _ENCRYPTION_KEY
    if _ENCRYPTION_KEY is None:
        # Try to load from file
        key_file = Path(__file__).parent.parent / ".encryption_key"
        if key_file.exists():
            try:
                with open(key_file, 'rb') as f:
                    _ENCRYPTION_KEY = f.read()
            except Exception as e:
                logger.error(f"Failed to load encryption key: {e}")

    if _ENCRYPTION_KEY is None:
        # Generate new key
        _ENCRYPTION_KEY = Fernet.generate_key()
        logger.warning("Generated new encryption key (store this securely!)")
        try:
            key_file = Path(__file__).parent.parent / ".encryption_key"
            key_file.parent.mkdir(exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(_ENCRYPTION_KEY)
            os.chmod(key_file, 0o600)  # Read/write for owner only
            logger.info(f"Encryption key saved to {key_file}")
        except Exception as e:
            logger.error(f"Failed to save encryption key: {e}")

    # Ensure key is bytes
    if isinstance(_ENCRYPTION_KEY, str):
        _ENCRYPTION_KEY = _ENCRYPTION_KEY.encode()

    global _cipher
    _cipher = Fernet(_ENCRYPTION_KEY)


def encrypt_value(value: str) -> str:
    """
    Encrypt a sensitive value.

    Args:
        value: Value to encrypt

    Returns:
        Encrypted value as base64 string
    """
    if _cipher is None:
        init_security()

    try:
        encrypted = _cipher.encrypt(value.encode())
        return base64.b64encode(encrypted).decode()
    except Exception as e:
        logger.error(f"Failed to encrypt value: {e}")
        raise


def decrypt_value(encrypted_value: str) -> str:
    """
    Decrypt a sensitive value.

    Args:
        encrypted_value: Encrypted value (base64 string)

    Returns:
        Decrypted value
    """
    if _cipher is None:
        init_security()

    try:
        encrypted_bytes = base64.b64decode(encrypted_value.encode())
        decrypted = _cipher.decrypt(encrypted_bytes)
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Failed to decrypt value: {e}")
        raise


def mask_api_key(api_key: str, visible_chars: int = 4) -> str:
    """
    Mask an API key for safe logging.

    Args:
        api_key: API key to mask
        visible_chars: Number of characters to show at the end

    Returns:
        Masked API key
    """
    if len(api_key) <= visible_chars:
        return "*" * len(api_key)
    return "*" * (len(api_key) - visible_chars) + api_key[-visible_chars:]


def validate_api_key_format(api_key: str) -> bool:
    """
    Validate API key format.

    Args:
        api_key: API key to validate

    Returns:
        True if valid format
    """
    # Basic format checks
    if not api_key:
        return False

    if len(api_key) < 10:
        return False

    # Check for suspicious patterns
    if api_key in ["test", "password", "123456"]:
        return False

    return True


def sanitize_input(value: str, max_length: int = 10000) -> str:
    """
    Sanitize user input to prevent injection attacks.

    Args:
        value: Input value to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized value
    """
    if not value:
        return ""

    # Truncate if too long
    if len(value) > max_length:
        value = value[:max_length]
        logger.warning(f"Input truncated to {max_length} characters")

    # Remove null bytes
    value = value.replace("\x00", "")

    # Remove control characters except common ones
    value = "".join(char for char in value if ord(char) >= 32 or char in "\t\n\r")

    return value


def validate_config_security(config_data: Dict[str, Any]) -> List[str]:
    """
    Validate configuration for security issues.

    Args:
        config_data: Configuration dictionary

    Returns:
        List of security warnings
    """
    warnings = []

    # Check for plain text API keys
    for provider in config_data.get("providers", []):
        api_key = provider.get("api_key", "")

        if api_key and not api_key.startswith("${") and not api_key.startswith("enc:"):
            warnings.append(
                f"Provider '{provider.get('name')}': API key is not using environment variable or encryption"
            )
            logger.warning(
                f"Provider '{provider.get('name')}' has unencrypted API key"
            )

        # Check for weak API keys
        if api_key and len(api_key) < 20:
            warnings.append(
                f"Provider '{provider.get('name')}': API key seems too short"
            )
            logger.warning(
                f"Provider '{provider.get('name')}' has a short API key"
            )

    return warnings


def secure_store_api_key(provider_name: str, api_key: str) -> str:
    """
    Securely store API key and return reference.

    Args:
        provider_name: Name of the provider
        api_key: API key to store

    Returns:
        Storage reference (environment variable name or encrypted value)
    """
    # Use environment variable if it's a standard format
    if os.getenv(api_key.replace("-", "_").upper()):
        return f"${{{api_key.replace('-', '_').upper()}}}"

    # Otherwise encrypt it
    encrypted = encrypt_value(api_key)
    storage_ref = f"enc:{encrypted}"

    logger.info(f"Stored API key for provider '{provider_name}' securely")
    return storage_ref


def secure_retrieve_api_key(storage_ref: str) -> str:
    """
    Retrieve API key from secure storage.

    Args:
        storage_ref: Storage reference

    Returns:
        API key
    """
    # Check if it's an environment variable reference
    if storage_ref.startswith("${") and storage_ref.endswith("}"):
        var_name = storage_ref[2:-1]
        api_key = os.getenv(var_name, "")
        if not api_key:
            logger.error(f"Environment variable {var_name} not set")
            raise ValueError(f"Environment variable {var_name} not set")
        return api_key

    # Check if it's encrypted
    if storage_ref.startswith("enc:"):
        encrypted_value = storage_ref[4:]
        return decrypt_value(encrypted_value)

    # Otherwise, return as-is (not secure!)
    logger.warning("API key is not securely stored")
    return storage_ref


def scan_for_secrets(file_path: str) -> List[str]:
    """
    Scan a file for potential secrets (API keys, passwords, etc.).

    Args:
        file_path: Path to file to scan

    Returns:
        List of potential secrets found
    """
    secrets = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Common secret patterns
        patterns = [
            r'api[_-]?key["\s:=]+([a-zA-Z0-9\-_]{20,})',
            r'secret[_-]?key["\s:=]+([a-zA-Z0-9\-_]{20,})',
            r'password["\s:=]+([a-zA-Z0-9\-_!@#$%^&*]{8,})',
            r'token["\s:=]+([a-zA-Z0-9\-_.]{20,})',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            secrets.extend(matches)

    except Exception as e:
        logger.error(f"Failed to scan file {file_path}: {e}")

    return secrets


def get_security_config() -> Dict[str, Any]:
    """
    Get security configuration.

    Returns:
        Dictionary with security settings
    """
    return {
        "encryption_enabled": _ENCRYPTION_KEY is not None,
        "api_key_encryption": True,
        "input_validation": True,
        "security_warnings": []
    }


# Initialize security on import
if os.getenv("ENABLE_SECURITY", "true").lower() == "true":
    init_security()
