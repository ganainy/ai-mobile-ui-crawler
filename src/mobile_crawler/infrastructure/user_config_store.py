"""Database management for user_config.db - user preferences and settings."""

import base64
import platform
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from mobile_crawler.config.paths import get_app_data_dir


class UserConfigStore:
    """Manages SQLite database for user configuration and preferences."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize user config store.

        Args:
            db_path: Path to database file. If None, uses default location.
        """
        if db_path is None:
            app_data_dir = get_app_data_dir()
            db_path = app_data_dir / "user_config.db"

        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory configured."""
        if self._connection is None:
            self._connection = sqlite3.connect(str(self.db_path))
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys=ON")
        return self._connection

    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def create_schema(self):
        """Create tables for user_config.db."""
        conn = self.get_connection()

        # user_config table - key-value settings
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                value_type TEXT NOT NULL,              -- 'string', 'int', 'float', 'bool', 'json'
                updated_at TEXT NOT NULL               -- ISO 8601
            )
        """)

        # secrets table - encrypted API keys
        conn.execute("""
            CREATE TABLE IF NOT EXISTS secrets (
                key TEXT PRIMARY KEY,                  -- e.g., 'gemini_api_key', 'openrouter_api_key'
                encrypted_value BLOB NOT NULL,
                updated_at TEXT NOT NULL               -- ISO 8601
            )
        """)

        # Create index for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_config_updated ON user_config(updated_at)")

        conn.commit()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key.

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Setting value converted to appropriate type, or default
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT value, value_type FROM user_config WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()

        if row is None:
            return default

        value_str, value_type = row["value"], row["value_type"]
        return self._convert_from_string(value_str, value_type)

    def set_setting(self, key: str, value: Any, value_type: Optional[str] = None):
        """Set a setting value.

        Args:
            key: Setting key
            value: Setting value
            value_type: Value type ('string', 'int', 'float', 'bool', 'json').
                       Auto-detected if not provided.
        """
        if value_type is None:
            value_type = self._detect_type(value)

        value_str = self._convert_to_string(value, value_type)

        conn = self.get_connection()
        cursor = conn.cursor()

        import datetime
        updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        cursor.execute("""
            INSERT OR REPLACE INTO user_config (key, value, value_type, updated_at)
            VALUES (?, ?, ?, ?)
        """, (key, value_str, value_type, updated_at))

        conn.commit()

    def delete_setting(self, key: str) -> bool:
        """Delete a setting.

        Args:
            key: Setting key to delete

        Returns:
            True if setting was deleted, False if not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM user_config WHERE key = ?", (key,))
        deleted = cursor.rowcount > 0

        conn.commit()
        return deleted

    def get_all_settings(self) -> dict[str, Any]:
        """Get all settings as a dictionary.

        Returns:
            Dictionary of all settings with converted values
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT key, value, value_type FROM user_config")
        rows = cursor.fetchall()

        settings = {}
        for row in rows:
            key, value_str, value_type = row["key"], row["value"], row["value_type"]
            settings[key] = self._convert_from_string(value_str, value_type)

        return settings

    def _derive_machine_key(self) -> bytes:
        """Derive a machine-bound encryption key using hardware identifiers.

        Returns:
            32-byte key for Fernet encryption
        """
        # Collect machine-specific identifiers
        identifiers = []

        # Platform and system info
        identifiers.append(platform.system())
        identifiers.append(platform.machine())
        identifiers.append(platform.node())  # Computer name

        # Try to get CPU info (cross-platform)
        try:
            import psutil
            cpu_info = psutil.cpu_freq()
            if cpu_info:
                identifiers.append(str(cpu_info.max))
        except (ImportError, AttributeError):
            pass

        # Try to get disk serial (Windows-specific but safe to try)
        try:
            import subprocess
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "diskdrive", "get", "serialnumber"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        serial = lines[1].strip()
                        if serial:
                            identifiers.append(serial)
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Use MAC address as fallback/additional identifier
        try:
            mac = uuid.getnode()
            identifiers.append(str(mac))
        except Exception:
            pass

        # Combine all identifiers
        combined = "|".join(identifiers)

        # Use PBKDF2 to derive a 32-byte key
        salt = b"mobile_crawler_salt_v1"  # Fixed salt for consistency
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(combined.encode()))
        return key

    def _get_fernet(self) -> Fernet:
        """Get Fernet cipher instance with machine-bound key.

        Returns:
            Fernet cipher for encryption/decryption
        """
        key = self._derive_machine_key()
        return Fernet(key)

    def encrypt_secret(self, plaintext: str) -> bytes:
        """Encrypt a plaintext secret.

        Args:
            plaintext: Secret value to encrypt

        Returns:
            Encrypted bytes
        """
        fernet = self._get_fernet()
        return fernet.encrypt(plaintext.encode())

    def decrypt_secret(self, encrypted_data: bytes) -> str:
        """Decrypt an encrypted secret.

        Args:
            encrypted_data: Encrypted bytes

        Returns:
            Decrypted plaintext

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails
        """
        fernet = self._get_fernet()
        return fernet.decrypt(encrypted_data).decode()

    def set_secret_plaintext(self, key: str, plaintext: str):
        """Set a secret by encrypting plaintext.

        Args:
            key: Secret key
            plaintext: Plaintext value to encrypt and store
        """
        encrypted = self.encrypt_secret(plaintext)
        self.set_secret(key, encrypted)

    def get_secret_plaintext(self, key: str) -> Optional[str]:
        """Get a secret by decrypting stored value.

        Args:
            key: Secret key

        Returns:
            Decrypted plaintext, or None if not found

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails
        """
        encrypted = self.get_secret(key)
        if encrypted is None:
            return None
        return self.decrypt_secret(encrypted)

    def get_secret(self, key: str) -> Optional[bytes]:
        """Get an encrypted secret value.

        Args:
            key: Secret key

        Returns:
            Encrypted value as bytes, or None if not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT encrypted_value FROM secrets WHERE key = ?", (key,))
        row = cursor.fetchone()

        return row["encrypted_value"] if row else None

    def set_secret(self, key: str, encrypted_value: bytes):
        """Set an encrypted secret value.

        Args:
            key: Secret key
            encrypted_value: Encrypted value as bytes
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        import datetime
        updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        cursor.execute("""
            INSERT OR REPLACE INTO secrets (key, encrypted_value, updated_at)
            VALUES (?, ?, ?)
        """, (key, encrypted_value, updated_at))

        conn.commit()

    def delete_secret(self, key: str) -> bool:
        """Delete a secret.

        Args:
            key: Secret key to delete

        Returns:
            True if secret was deleted, False if not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM secrets WHERE key = ?", (key,))
        deleted = cursor.rowcount > 0

        conn.commit()
        return deleted

    def _detect_type(self, value: Any) -> str:
        """Detect the type of a value for storage."""
        if isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, (list, dict)):
            return "json"
        else:
            return "string"

    def _convert_to_string(self, value: Any, value_type: str) -> str:
        """Convert a value to string for storage."""
        if value_type == "bool":
            return "true" if value else "false"
        elif value_type == "json":
            import json
            return json.dumps(value)
        else:
            return str(value)

    def _convert_from_string(self, value_str: str, value_type: str) -> Any:
        """Convert a string back to the appropriate type."""
        if value_type == "bool":
            return value_str.lower() == "true"
        elif value_type == "int":
            return int(value_str)
        elif value_type == "float":
            return float(value_str)
        elif value_type == "json":
            import json
            return json.loads(value_str)
        else:
            return value_str
