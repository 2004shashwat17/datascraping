"""
Secure credential vault for storing social media login credentials.
Uses encryption and secure storage for browser automation.
"""

import os
import json
import secrets
import hashlib
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from app.core.config import get_settings
from app.core.mongodb import get_database
from app.models.mongo_models import User

logger = logging.getLogger(__name__)

class CredentialVaultService:
    """Secure service for storing and retrieving social media credentials."""

    def __init__(self):
        self.settings = get_settings()
        self.db = get_database()
        self.vault_path = Path("data/credential_vault")
        self.vault_path.mkdir(parents=True, exist_ok=True)

        # Initialize encryption key
        self._init_encryption_key()

    def _init_encryption_key(self):
        """Initialize or load encryption key."""
        key_file = self.vault_path / "master.key"

        if key_file.exists():
            with open(key_file, 'rb') as f:
                self.key = f.read()
        else:
            # Generate a new key
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            master_password = secrets.token_hex(32)
            self.key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

            # Save key info (in production, this should be more secure)
            key_data = {
                "salt": base64.b64encode(salt).decode(),
                "master_password": master_password,
                "created_at": datetime.utcnow().isoformat()
            }

            with open(key_file, 'wb') as f:
                f.write(self.key)

            with open(self.vault_path / "key_info.json", 'w') as f:
                json.dump(key_data, f, indent=2)

        self.cipher = Fernet(self.key)

    def _get_user_vault_path(self, user_id: str) -> Path:
        """Get the vault path for a specific user."""
        return self.vault_path / user_id

    def _encrypt_data(self, data: str) -> str:
        """Encrypt string data."""
        return self.cipher.encrypt(data.encode()).decode()

    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

    async def store_credentials(self, user_id: str, platform: str,
                              credentials: Dict[str, str]) -> bool:
        """Store encrypted credentials for a platform."""
        try:
            user_vault = self._get_user_vault_path(user_id)
            user_vault.mkdir(exist_ok=True)

            # Encrypt credentials
            encrypted_creds = self._encrypt_data(json.dumps(credentials))

            credential_data = {
                "platform": platform,
                "credentials": encrypted_creds,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "last_used": None
            }

            # Save to file
            cred_file = user_vault / f"{platform}.json"
            with open(cred_file, 'w') as f:
                json.dump(credential_data, f, indent=2)

            logger.info(f"🔐 Stored credentials for {platform} (User: {user_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
            return False

    async def get_credentials(self, user_id: str, platform: str) -> Optional[Dict[str, str]]:
        """Retrieve decrypted credentials for a platform."""
        try:
            user_vault = self._get_user_vault_path(user_id)
            cred_file = user_vault / f"{platform}.json"

            if not cred_file.exists():
                return None

            with open(cred_file, 'r') as f:
                data = json.load(f)

            # Decrypt credentials
            decrypted_creds = self._decrypt_data(data["credentials"])
            credentials = json.loads(decrypted_creds)

            # Update last used timestamp
            data["last_used"] = datetime.utcnow().isoformat()
            with open(cred_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"🔓 Retrieved credentials for {platform} (User: {user_id})")
            return credentials

        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {e}")
            return None

    async def delete_credentials(self, user_id: str, platform: str) -> bool:
        """Delete stored credentials for a platform."""
        try:
            user_vault = self._get_user_vault_path(user_id)
            cred_file = user_vault / f"{platform}.json"

            if cred_file.exists():
                cred_file.unlink()
                logger.info(f"🗑️ Deleted credentials for {platform} (User: {user_id})")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete credentials: {e}")
            return False

    async def list_stored_platforms(self, user_id: str) -> list[str]:
        """List platforms with stored credentials for a user."""
        try:
            user_vault = self._get_user_vault_path(user_id)
            if not user_vault.exists():
                return []

            platforms = []
            for cred_file in user_vault.glob("*.json"):
                platform = cred_file.stem
                platforms.append(platform)

            return platforms

        except Exception as e:
            logger.error(f"Failed to list stored platforms: {e}")
            return []

    async def validate_credentials(self, user_id: str, platform: str) -> bool:
        """Validate that stored credentials exist and are accessible."""
        try:
            creds = await self.get_credentials(user_id, platform)
            return creds is not None and bool(creds)
        except Exception:
            return False

    async def update_credentials(self, user_id: str, platform: str,
                               new_credentials: Dict[str, str]) -> bool:
        """Update existing credentials for a platform."""
        return await self.store_credentials(user_id, platform, new_credentials)

# Global service instance
credential_vault = CredentialVaultService()