"""Encryption functionality for database."""
import os
import logging
from pathlib import Path
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages encryption for sensitive data."""

    def __init__(self):
        """Initialize encryption manager."""
        self.encryption_key = self._get_or_create_key()
        self.fernet = Fernet(self.encryption_key)

    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key."""
        # First, try to get from environment variable (preferred for production)
        env_key = os.getenv("ENCRYPTION_KEY")
        if env_key:
            try:
                # Validate that it's a valid Fernet key
                Fernet(env_key.encode())
                return env_key.encode()
            except Exception as e:
                logger.error(f"Invalid ENCRYPTION_KEY from environment: {e}")
                raise ValueError("ENCRYPTION_KEY must be a valid Fernet key (32 bytes base64-encoded)")
        
        # Fallback to file-based key
        key_file = Path(__file__).parent.parent.parent / "data" / ".key"
        if key_file.exists():
            # 读取现有密钥
            try:
                with open(key_file, 'rb') as f:
                    key = f.read()
                    # Validate key
                    Fernet(key)
                    return key
            except Exception as e:
                logger.warning(f"Invalid key file, generating new key: {e}")
                # Generate new key if file is corrupted
                encryption_key = Fernet.generate_key()
                key_file.parent.mkdir(parents=True, exist_ok=True)
                with open(key_file, 'wb') as f:
                    f.write(encryption_key)
                os.chmod(key_file, 0o666)
                return encryption_key
        else:
            # 生成新密钥
            encryption_key = Fernet.generate_key()
            # 确保目录存在
            key_file.parent.mkdir(parents=True, exist_ok=True)
            # 保存密钥文件
            with open(key_file, 'wb') as f:
                f.write(encryption_key)
            # 设置文件权限
            os.chmod(key_file, 0o666)
            logger.warning(
                f"Generated new encryption key at {key_file}. "
                "For production, set ENCRYPTION_KEY environment variable."
            )
            return encryption_key

    def encrypt(self, data: str) -> str:
        """Encrypt data."""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data."""
        return self.fernet.decrypt(encrypted_data.encode()).decode()

