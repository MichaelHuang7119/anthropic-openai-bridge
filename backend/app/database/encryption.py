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
        key_file = Path(__file__).parent.parent.parent / "data" / ".key"
        if key_file.exists():
            # 读取现有密钥
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # 生成新密钥
            encryption_key = Fernet.generate_key()
            # 保存密钥文件（可选，如果设置了环境变量则使用环境变量）
            env_key = os.getenv("ENCRYPTION_KEY")
            if env_key:
                encryption_key = env_key.encode()
            else:
                # 确保目录存在
                key_file.parent.mkdir(parents=True, exist_ok=True)
                # 保存密钥文件
                with open(key_file, 'wb') as f:
                    f.write(encryption_key)
                # 设置文件权限（仅所有者可读写）
                os.chmod(key_file, 0o600)

            return encryption_key

    def encrypt(self, data: str) -> str:
        """Encrypt data."""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data."""
        return self.fernet.decrypt(encrypted_data.encode()).decode()

