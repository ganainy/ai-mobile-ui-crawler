"""Tests for PreCrawlValidator."""

from unittest.mock import Mock

import pytest

from mobile_crawler.core.pre_crawl_validator import (
    PreCrawlValidator,
    ValidationError,
)


class TestValidationError:
    """Tests for ValidationError dataclass."""

    def test_creation(self):
        """Test ValidationError creation."""
        error = ValidationError(
            field="test_field",
            message="Test message",
            severity="error"
        )

        assert error.field == "test_field"
        assert error.message == "Test message"
        assert error.severity == "error"


class TestPreCrawlValidator:
    """Tests for PreCrawlValidator."""

    def test_init(self):
        """Test initialization."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_model = Mock()
        mock_config = Mock()
        mock_creds = Mock()

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        assert validator._appium_driver is mock_appium
        assert validator._device_detector is mock_device
        assert validator._model_detector is mock_model
        assert validator._config_manager is mock_config
        assert validator._credential_store is mock_creds

    def test_validate_all_valid(self):
        """Test validation with all valid inputs."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = [
            Mock(id="emulator-5554", model="Pixel 5", android_version="13.0")
        ]
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")
        ]
        mock_config = Mock()
        mock_config.get.return_value = "configured_value"
        mock_creds = Mock()
        mock_creds.get.return_value = "api_key"

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="com.example.app",
            ai_provider="gemini",
            ai_model="gemini-pro-vision",
        )

        assert errors == []

    def test_validate_no_device(self):
        """Test validation with no device connected."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = []
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")
        ]
        mock_config = Mock()
        mock_config.get.return_value = "configured_value"  # Avoid optional warnings
        mock_creds = Mock()
        mock_creds.get.return_value = "api_key"

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="com.example.app",
            ai_provider="gemini",
            ai_model="gemini-pro-vision",
        )

        # Should have device error and pcapdroid warning (since no device connected)
        assert len(errors) == 2
        assert errors[0].field == "device"
        assert errors[0].severity == "error"
        assert errors[1].field == "pcapdroid"
        assert errors[1].severity == "warning"

    def test_validate_device_not_connected(self):
        """Test validation with specific device not connected."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = [
            Mock(id="emulator-5554", model="Pixel 5", android_version="13.0")
        ]
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")
        ]
        mock_config = Mock()
        mock_config.get.return_value = "configured_value"  # Avoid optional warnings
        mock_creds = Mock()
        mock_creds.get.return_value = "api_key"

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5556",  # Different ID
            app_package="com.example.app",
            ai_provider="gemini",
            ai_model="gemini-pro-vision",
        )

        assert len(errors) == 1
        assert errors[0].field == "device"
        assert "emulator-5556" in errors[0].message

    def test_validate_no_app_package(self):
        """Test validation with no app package - app_package None skips validation."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = [
            Mock(id="emulator-5554")
        ]
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")
        ]
        mock_config = Mock()
        mock_config.get.return_value = "configured_value"  # Avoid optional warnings
        mock_creds = Mock()
        mock_creds.get.return_value = "api_key"

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package=None,
            ai_provider="gemini",
            ai_model="gemini-pro-vision",
        )

        # app_package is None, so app validation is skipped
        assert len(errors) == 0

    def test_validate_invalid_app_package_format(self):
        """Test validation with invalid app package format."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = [
            Mock(id="emulator-5554")
        ]
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")
        ]
        mock_config = Mock()
        mock_config.get.return_value = "configured_value"  # Avoid optional warnings
        mock_creds = Mock()
        mock_creds.get.return_value = "api_key"

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="invalid_package",  # Missing dots
            ai_provider="gemini",
            ai_model="gemini-pro-vision",
        )

        assert len(errors) == 1
        assert errors[0].field == "app_package"
        assert "Invalid app package format" in errors[0].message

    def test_validate_no_ai_provider(self):
        """Test validation with no AI provider."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = [
            Mock(id="emulator-5554")
        ]
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")
        ]
        mock_config = Mock()
        mock_config.get.return_value = "configured_value"  # Avoid optional warnings
        mock_creds = Mock()

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="com.example.app",
            ai_provider=None,
            ai_model="gemini-pro-vision",
        )

        assert len(errors) == 1
        assert errors[0].field == "ai_provider"
        assert errors[0].severity == "error"

    def test_validate_no_ai_model(self):
        """Test validation with no AI model."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = [
            Mock(id="emulator-5554")
        ]
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")
        ]
        mock_config = Mock()
        mock_config.get.return_value = "configured_value"  # Avoid optional warnings
        mock_creds = Mock()

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="com.example.app",
            ai_provider="gemini",
            ai_model=None,
        )

        assert len(errors) == 1
        assert errors[0].field == "ai_model"
        assert errors[0].severity == "error"

    def test_validate_model_not_vision_capable(self):
        """Test validation with non-vision-capable model."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = [
            Mock(id="emulator-5554")
        ]
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")  # Different model
        ]
        mock_config = Mock()
        mock_config.get.return_value = "configured_value"  # Avoid optional warnings
        mock_creds = Mock()
        mock_creds.get.return_value = "api_key"

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="com.example.app",
            ai_provider="gemini",
            ai_model="text-only-model",
        )

        assert len(errors) == 1
        assert errors[0].field == "ai_model"
        assert errors[0].severity == "error"
        assert "not available" in errors[0].message.lower()

    def test_validate_model_not_available(self):
        """Test validation with model not in available list."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = [
            Mock(id="emulator-5554")
        ]
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")
        ]
        mock_config = Mock()
        mock_creds = Mock()

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="com.example.app",
            ai_provider="gemini",
            ai_model="gemini-pro-2",  # Different model
        )

        assert len(errors) == 1
        assert errors[0].field == "ai_model"
        assert errors[0].severity == "error"
        assert "not available" in errors[0].message.lower()

    def test_validate_no_gemini_api_key(self):
        """Test validation with missing Gemini API key."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = [
            Mock(id="emulator-5554")
        ]
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")
        ]
        mock_config = Mock()
        mock_creds = Mock()
        mock_creds.get.return_value = None  # No API key

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="com.example.app",
            ai_provider="gemini",
            ai_model="gemini-pro-vision",
        )

        assert len(errors) == 1
        assert errors[0].field == "gemini_api_key"
        assert errors[0].severity == "error"

    def test_validate_no_openrouter_api_key(self):
        """Test validation with missing OpenRouter API key."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = [
            Mock(id="emulator-5554")
        ]
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gpt-4-vision")
        ]
        mock_config = Mock()
        mock_creds = Mock()
        mock_creds.get.return_value = None  # No API key

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="com.example.app",
            ai_provider="openrouter",
            ai_model="gpt-4-vision",
        )

        assert len(errors) == 1
        assert errors[0].field == "openrouter_api_key"
        assert errors[0].severity == "error"

    def test_validate_ollama_no_api_key_required(self):
        """Test that Ollama doesn't require API key."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = [
            Mock(id="emulator-5554")
        ]
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="llama3.2-vision")
        ]
        mock_config = Mock()
        mock_creds = Mock()

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="com.example.app",
            ai_provider="ollama",
            ai_model="llama3.2-vision",
        )

        # Ollama should not require API key
        api_key_errors = [e for e in errors if e.field == "gemini_api_key" or e.field == "openrouter_api_key"]
        assert len(api_key_errors) == 0

    def test_validate_mobsf_not_configured(self):
        """Test MobSF warning when not configured."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = [
            Mock(id="emulator-5554")
        ]
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")
        ]
        mock_config = Mock()
        mock_config.get.return_value = None  # Not configured
        mock_creds = Mock()

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="com.example.app",
            ai_provider="gemini",
            ai_model="gemini-pro-vision",
        )

        mobsf_warnings = [e for e in errors if e.field == "mobsf"]
        assert len(mobsf_warnings) == 1
        assert mobsf_warnings[0].severity == "warning"

    def test_validate_pcapdroid_not_installed(self):
        """Test PCAPdroid warning when not installed."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = [
            Mock(id="emulator-5554")
        ]
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")
        ]
        mock_config = Mock()
        mock_config.get.return_value = False  # Not installed
        mock_creds = Mock()

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="com.example.app",
            ai_provider="gemini",
            ai_model="gemini-pro-vision",
        )

        pcapdroid_warnings = [e for e in errors if e.field == "pcapdroid"]
        assert len(pcapdroid_warnings) == 1
        assert pcapdroid_warnings[0].severity == "warning"

    def test_validate_video_not_available(self):
        """Test video warning when not available."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = [
            Mock(id="emulator-5554")
        ]
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")
        ]
        mock_config = Mock()
        mock_config.get.return_value = False  # Not available
        mock_creds = Mock()

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="com.example.app",
            ai_provider="gemini",
            ai_model="gemini-pro-vision",
        )

        video_warnings = [e for e in errors if e.field == "video"]
        assert len(video_warnings) == 1
        assert video_warnings[0].severity == "warning"

    def test_has_errors(self):
        """Test has_errors method."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = []
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")
        ]
        mock_config = Mock()
        mock_config.get.return_value = "configured_value"  # Avoid optional warnings
        mock_creds = Mock()
        mock_creds.get.return_value = "api_key"

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="com.example.app",
            ai_provider="gemini",
            ai_model="gemini-pro-vision",
        )

        assert validator.has_errors(errors) is True

    def test_has_errors_no_errors(self):
        """Test has_errors with no errors."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = [
            Mock(id="emulator-5554")
        ]
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")
        ]
        mock_config = Mock()
        mock_creds = Mock()
        mock_creds.get.return_value = "api_key"

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="com.example.app",
            ai_provider="gemini",
            ai_model="gemini-pro-vision",
        )

        assert validator.has_errors(errors) is False

    def test_has_warnings_only(self):
        """Test has_warnings_only with only warnings."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = [
            Mock(id="emulator-5554")
        ]
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")
        ]
        mock_config = Mock()
        mock_config.get.return_value = None  # MobSF not configured
        mock_creds = Mock()

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="com.example.app",
            ai_provider="gemini",
            ai_model="gemini-pro-vision",
        )

        assert validator.has_warnings_only(errors) is True

    def test_has_warnings_only_with_error(self):
        """Test has_warnings_only with error present."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = []
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")
        ]
        mock_config = Mock()
        mock_config.get.return_value = "configured_value"  # Avoid optional warnings
        mock_creds = Mock()
        mock_creds.get.return_value = "api_key"

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="com.example.app",
            ai_provider="gemini",
            ai_model="gemini-pro-vision",
        )

        assert validator.has_warnings_only(errors) is False

    def test_multiple_errors(self):
        """Test validation with multiple errors."""
        mock_appium = Mock()
        mock_device = Mock()
        mock_device.get_connected_devices.return_value = []
        mock_model = Mock()
        mock_model.get_vision_models.return_value = [
            Mock(id="gemini-pro-vision")
        ]
        mock_config = Mock()
        mock_config.get.return_value = "configured_value"  # Avoid optional warnings
        mock_creds = Mock()
        mock_creds.get.return_value = None

        validator = PreCrawlValidator(
            appium_driver=mock_appium,
            device_detector=mock_device,
            model_detector=mock_model,
            config_manager=mock_config,
            credential_store=mock_creds,
        )

        errors = validator.validate(
            device_id="emulator-5554",
            app_package="com.example.app",
            ai_provider="gemini",
            ai_model="gemini-pro-vision",
        )

        # Should have errors for device, app, and API key, plus pcapdroid warning
        assert len(errors) == 3
        error_fields = [e.field for e in errors]
        assert "device" in error_fields
        assert "gemini_api_key" in error_fields
        assert "pcapdroid" in error_fields
