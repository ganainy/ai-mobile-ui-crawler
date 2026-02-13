"""Credential store for encrypting sensitive data."""

import base64
import socket
import uuid
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class CredentialStore:
    """Handles encryption and decryption of sensitive credentials using machine-bound keys."""

    def __init__(self, machine_id: Optional[str] = None):
        """Initialize credential store with machine-bound encryption.
        
        Args:
            machine_id: Optional machine identifier override for testing
        """
        self._fernet = self._create_fernet(machine_id)

    def _create_fernet(self, machine_id: Optional[str] = None) -> Fernet:
        """Create Fernet cipher with key derived from machine identifier.
        
        Args:
            machine_id: Machine identifier, auto-detected if None
            
        Returns:
            Fernet cipher instance
        """
        if machine_id is None:
            hostname = socket.gethostname()
            mac = uuid.getnode()
            machine_id = f"{hostname}:{mac}"
        
        # Use machine_id as both password and salt for derivation
        password = machine_id.encode()
        salt = machine_id.encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return Fernet(key)

    def encrypt(self, value: str) -> bytes:
        """Encrypt a string value.
        
        Args:
            value: Plain text string to encrypt
            
        Returns:
            Encrypted bytes suitable for BLOB storage
        """
        return self._fernet.encrypt(value.encode())

    def decrypt(self, encrypted: bytes) -> str:
        """Decrypt encrypted bytes back to string.
        
        Args:
            encrypted: Encrypted bytes from encrypt()
            
        Returns:
            Decrypted plain text string
        """
        return self._fernet.decrypt(encrypted).decode()