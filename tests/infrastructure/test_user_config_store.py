"""Tests for user_config_store.py."""

import tempfile
from pathlib import Path

import pytest

from mobile_crawler.infrastructure.user_config_store import UserConfigStore


@pytest.fixture
def temp_config_path():
    """Create a temporary config database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    # Cleanup
    if path.exists():
        path.unlink()


@pytest.fixture
def config_store(temp_config_path):
    """Create a config store with temporary file."""
    store = UserConfigStore(temp_config_path)
    store.create_schema()
    yield store
    store.close()


class TestUserConfigStore:
    """Test UserConfigStore functionality."""

    def test_schema_creation(self, config_store):
        """Test schema creation creates required tables."""
        conn = config_store.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "user_config" in tables
        assert "secrets" in tables

    def test_set_and_get_setting_string(self, config_store):
        """Test setting and getting string values."""
        config_store.set_setting("test_key", "test_value")
        assert config_store.get_setting("test_key") == "test_value"

    def test_set_and_get_setting_int(self, config_store):
        """Test setting and getting integer values."""
        config_store.set_setting("int_key", 42)
        assert config_store.get_setting("int_key") == 42
        assert isinstance(config_store.get_setting("int_key"), int)

    def test_set_and_get_setting_bool(self, config_store):
        """Test setting and getting boolean values."""
        config_store.set_setting("bool_key", True)
        assert config_store.get_setting("bool_key") is True
        assert isinstance(config_store.get_setting("bool_key"), bool)

    def test_set_and_get_setting_float(self, config_store):
        """Test setting and getting float values."""
        config_store.set_setting("float_key", 3.14)
        assert config_store.get_setting("float_key") == 3.14
        assert isinstance(config_store.get_setting("float_key"), float)

    def test_set_and_get_setting_json(self, config_store):
        """Test setting and getting JSON values."""
        test_dict = {"key": "value", "number": 123}
        config_store.set_setting("json_key", test_dict)
        result = config_store.get_setting("json_key")
        assert result == test_dict
        assert isinstance(result, dict)

    def test_get_setting_default(self, config_store):
        """Test getting non-existent setting returns default."""
        assert config_store.get_setting("nonexistent") is None
        assert config_store.get_setting("nonexistent", "default") == "default"

    def test_delete_setting(self, config_store):
        """Test deleting a setting."""
        config_store.set_setting("delete_key", "value")
        assert config_store.get_setting("delete_key") == "value"

        assert config_store.delete_setting("delete_key") is True
        assert config_store.get_setting("delete_key") is None

        # Deleting non-existent key
        assert config_store.delete_setting("nonexistent") is False

    def test_get_all_settings(self, config_store):
        """Test getting all settings."""
        config_store.set_setting("key1", "value1")
        config_store.set_setting("key2", 42)
        config_store.set_setting("key3", True)

        all_settings = config_store.get_all_settings()
        assert all_settings["key1"] == "value1"
        assert all_settings["key2"] == 42
        assert all_settings["key3"] is True

    def test_set_and_get_secret(self, config_store):
        """Test setting and getting encrypted secrets."""
        test_data = b"encrypted_secret_data"
        config_store.set_secret("api_key", test_data)

        result = config_store.get_secret("api_key")
        assert result == test_data

    def test_get_secret_not_found(self, config_store):
        """Test getting non-existent secret returns None."""
        assert config_store.get_secret("nonexistent") is None

    def test_delete_secret(self, config_store):
        """Test deleting a secret."""
        test_data = b"secret_data"
        config_store.set_secret("delete_secret", test_data)
        assert config_store.get_secret("delete_secret") == test_data

        assert config_store.delete_secret("delete_secret") is True
        assert config_store.get_secret("delete_secret") is None

        # Deleting non-existent secret
        assert config_store.delete_secret("nonexistent") is False

    def test_type_detection(self, config_store):
        """Test automatic type detection."""
        # Test various types
        config_store.set_setting("str", "hello")
        config_store.set_setting("int", 123)
        config_store.set_setting("float", 45.67)
        config_store.set_setting("bool", False)
        config_store.set_setting("json", {"key": "value"})

        # Verify types are preserved
        assert isinstance(config_store.get_setting("str"), str)
        assert isinstance(config_store.get_setting("int"), int)
        assert isinstance(config_store.get_setting("float"), float)
        assert isinstance(config_store.get_setting("bool"), bool)
        assert isinstance(config_store.get_setting("json"), dict)

    def test_encrypt_decrypt_secret(self, config_store):
        """Test encrypting and decrypting secrets."""
        plaintext = "my_secret_api_key_12345"

        # Encrypt
        encrypted = config_store.encrypt_secret(plaintext)
        assert isinstance(encrypted, bytes)
        assert encrypted != plaintext.encode()

        # Decrypt
        decrypted = config_store.decrypt_secret(encrypted)
        assert decrypted == plaintext

    def test_set_get_secret_plaintext(self, config_store):
        """Test setting and getting secrets with automatic encryption/decryption."""
        key = "gemini_api_key"
        plaintext = "AIzaSyDummyApiKeyForTesting123"

        # Set plaintext (should encrypt automatically)
        config_store.set_secret_plaintext(key, plaintext)

        # Get plaintext (should decrypt automatically)
        result = config_store.get_secret_plaintext(key)
        assert result == plaintext

    def test_get_secret_plaintext_not_found(self, config_store):
        """Test getting non-existent secret plaintext returns None."""
        assert config_store.get_secret_plaintext("nonexistent_key") is None

    def test_key_derivation_consistency(self, config_store):
        """Test that key derivation is consistent for the same machine."""
        # Derive key multiple times - should be the same
        key1 = config_store._derive_machine_key()
        key2 = config_store._derive_machine_key()

        assert key1 == key2
        assert len(key1) == 44  # Fernet keys are 32 bytes base64 encoded

    def test_encryption_different_instances(self, config_store, temp_config_path):
        """Test that different store instances can encrypt/decrypt each other's data."""
        # Create two separate store instances
        store1 = UserConfigStore(temp_config_path)
        store1.create_schema()
        store2 = UserConfigStore(temp_config_path)

        plaintext = "shared_secret_value"

        # Store1 encrypts and stores
        store1.set_secret_plaintext("shared_key", plaintext)

        # Store2 should be able to decrypt it (same machine, same key)
        result = store2.get_secret_plaintext("shared_key")
        assert result == plaintext

        store1.close()
        store2.close()

    def test_encryption_fails_with_wrong_key(self, config_store):
        """Test that decryption fails with invalid data."""
        from cryptography.fernet import InvalidToken

        # Try to decrypt invalid data
        with pytest.raises(InvalidToken):
            config_store.decrypt_secret(b"invalid_encrypted_data")

    def test_secret_storage_separate_from_settings(self, config_store):
        """Test that secrets and settings are stored separately."""
        # Set a setting and a secret with same key
        config_store.set_setting("same_key", "setting_value")
        config_store.set_secret_plaintext("same_key", "secret_value")

        # They should be independent
        assert config_store.get_setting("same_key") == "setting_value"
        assert config_store.get_secret_plaintext("same_key") == "secret_value"

        # Deleting setting shouldn't affect secret
        config_store.delete_setting("same_key")
        assert config_store.get_setting("same_key") is None
        assert config_store.get_secret_plaintext("same_key") == "secret_value"
