"""Tests for credential store."""

import pytest

from mobile_crawler.infrastructure.credential_store import CredentialStore


class TestCredentialStore:
    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypt followed by decrypt returns original value."""
        store = CredentialStore(machine_id="test_machine")
        original = "my_secret_api_key"
        
        encrypted = store.encrypt(original)
        decrypted = store.decrypt(encrypted)
        
        assert decrypted == original
        assert isinstance(encrypted, bytes)

    def test_encrypt_decrypt_different_instances_same_machine(self):
        """Test that different instances with same machine_id can decrypt each other's data."""
        machine_id = "test_machine_123"
        store1 = CredentialStore(machine_id=machine_id)
        store2 = CredentialStore(machine_id=machine_id)
        
        original = "shared_secret"
        encrypted = store1.encrypt(original)
        decrypted = store2.decrypt(encrypted)
        
        assert decrypted == original

    def test_encrypt_decrypt_different_machine_ids_fail(self):
        """Test that data encrypted with one machine_id cannot be decrypted with another."""
        store1 = CredentialStore(machine_id="machine1")
        store2 = CredentialStore(machine_id="machine2")
        
        original = "secret_data"
        encrypted = store1.encrypt(original)
        
        with pytest.raises(Exception):  # Fernet decryption will fail with wrong key
            store2.decrypt(encrypted)

    def test_encrypt_returns_bytes(self):
        """Test that encrypt returns bytes."""
        store = CredentialStore(machine_id="test")
        result = store.encrypt("test_value")
        
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_decrypt_returns_string(self):
        """Test that decrypt returns string."""
        store = CredentialStore(machine_id="test")
        original = "test_value"
        encrypted = store.encrypt(original)
        decrypted = store.decrypt(encrypted)
        
        assert isinstance(decrypted, str)
        assert decrypted == original