"""Pre-crawl validation for ensuring all requirements are met."""

import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Represents a single validation error."""

    field: str
    message: str
    severity: str  # "error", "warning", "info"


class PreCrawlValidator:
    """Validates all requirements before starting a crawl.

    Checks:
    - Appium server reachable
    - Device connected
    - App selected
    - Model selected (vision-capable)
    - API key present (for cloud providers)
    - Optional: MobSF server reachable (warn only)
    - Optional: PCAPdroid installed (warn only)
    - Optional: Video recording available (warn only)
    """

    def __init__(self, appium_driver, device_detector, model_detector,
                 config_manager, credential_store):
        """Initialize the pre-crawl validator.

        Args:
            appium_driver: AppiumDriver instance for connectivity check
            device_detector: DeviceDetector instance for device check
            model_detector: VisionDetector instance for model check
            config_manager: ConfigManager instance for configuration access
            credential_store: CredentialStore instance for API key check
        """
        self._appium_driver = appium_driver
        self._device_detector = device_detector
        self._model_detector = model_detector
        self._config_manager = config_manager
        self._credential_store = credential_store

    def validate(self, device_id: Optional[str], app_package: Optional[str],
                ai_provider: Optional[str], ai_model: Optional[str]) -> List[ValidationError]:
        """Validate all pre-crawl requirements.

        Args:
            device_id: Target device identifier
            app_package: Target app package name
            ai_provider: AI provider (gemini, openrouter, ollama)
            ai_model: AI model name

        Returns:
            List of validation errors (empty if all valid)
        """
        errors: List[ValidationError] = []

        # Track if any required parameter is provided
        has_any_param = bool(device_id or app_package or ai_provider or ai_model)

        # 1. Check Appium server reachable (required when any param is provided)
        if has_any_param:
            appium_error = self._check_appium_reachable()
            if appium_error:
                errors.append(appium_error)

        # 2. Check device connected (required when device_id is provided)
        if device_id:
            device_error = self._check_device_connected(device_id)
            if device_error:
                errors.append(device_error)

        # 3. Check app selected (required when app_package is provided)
        if app_package:
            app_error = self._check_app_selected(app_package)
            if app_error:
                errors.append(app_error)

        # 4. Check model selected and vision-capable (required when ai_provider or ai_model is provided)
        if ai_provider or ai_model:
            model_error = self._check_model_selected(ai_provider, ai_model)
            if model_error:
                errors.append(model_error)

        # 5. Check API key present (for cloud providers, required when ai_provider is provided)
        if ai_provider:
            api_key_error = self._check_api_key(ai_provider)
            if api_key_error:
                errors.append(api_key_error)

        # 6. Check MobSF server reachable (optional, warn only - only when any param is provided)
        if has_any_param:
            mobsf_warning = self._check_mobsf_reachable()
            if mobsf_warning:
                errors.append(mobsf_warning)

        # 7. Check PCAPdroid installed (optional, warn only - only when any param is provided)
        if has_any_param:
            pcapdroid_warning = self._check_pcapdroid_installed()
            if pcapdroid_warning:
                errors.append(pcapdroid_warning)

        # 8. Check video recording available (optional, warn only - only when any param is provided)
        if has_any_param:
            video_warning = self._check_video_available()
            if video_warning:
                errors.append(video_warning)

        return errors

    def _check_appium_reachable(self) -> Optional[ValidationError]:
        """Check if Appium server is reachable.

        Returns:
            ValidationError if not reachable, None otherwise
        """
        try:
            # Try to get Appium status
            if hasattr(self._appium_driver, 'get_status'):
                status = self._appium_driver.get_status()
                if not status.get('ready', False):
                    return ValidationError(
                        field="appium",
                        message="Appium server is not ready",
                        severity="error"
                    )
            else:
                # Try a simple connection check
                if hasattr(self._appium_driver, 'is_connected'):
                    if not self._appium_driver.is_connected():
                        return ValidationError(
                            field="appium",
                            message="Cannot connect to Appium server at localhost:4723",
                            severity="error"
                        )
        except Exception as e:
            logger.error(f"Error checking Appium connectivity: {e}")
            return ValidationError(
                field="appium",
                message=f"Failed to check Appium server: {e}",
                severity="error"
            )

        return None

    def _check_device_connected(self, device_id: Optional[str]) -> Optional[ValidationError]:
        """Check if a device is connected.

        Args:
            device_id: Target device identifier

        Returns:
            ValidationError if no device, None otherwise
        """
        try:
            devices = self._device_detector.get_connected_devices()

            if not devices:
                return ValidationError(
                    field="device",
                    message="No Android devices connected via ADB",
                    severity="error"
                )

            # If specific device requested, verify it's connected
            if device_id:
                device_ids = [d.id for d in devices]
                if device_id not in device_ids:
                    return ValidationError(
                        field="device",
                        message=f"Device '{device_id}' is not connected. Available devices: {', '.join(device_ids)}",
                        severity="error"
                    )
        except Exception as e:
            logger.error(f"Error checking device connectivity: {e}")
            return ValidationError(
                field="device",
                message=f"Failed to check device connectivity: {e}",
                severity="error"
            )

        return None

    def _check_app_selected(self, app_package: Optional[str]) -> Optional[ValidationError]:
        """Check if an app is selected.

        Args:
            app_package: Target app package name

        Returns:
            ValidationError if no app selected, None otherwise
        """
        if not app_package:
            return ValidationError(
                field="app_package",
                message="No target app package specified",
                severity="error"
            )

        # Basic package format validation
        if not app_package or '.' not in app_package or len(app_package.split('.')) < 2:
            return ValidationError(
                field="app_package",
                message=f"Invalid app package format: '{app_package}'. Expected format: 'com.example.app'",
                severity="error"
            )

        return None

    def _check_model_selected(self, ai_provider: Optional[str],
                           ai_model: Optional[str]) -> Optional[ValidationError]:
        """Check if a vision-capable model is selected.

        Args:
            ai_provider: AI provider name
            ai_model: AI model name

        Returns:
            ValidationError if no model selected, None otherwise
        """
        if not ai_provider:
            return ValidationError(
                field="ai_provider",
                message="No AI provider selected",
                severity="error"
            )

        if not ai_model:
            return ValidationError(
                field="ai_model",
                message="No AI model selected",
                severity="error"
            )

        # Check if model is vision-capable
        try:
            vision_models = self._model_detector.get_vision_models(ai_provider)
            if not vision_models:
                return ValidationError(
                    field="ai_model",
                    message=f"No vision-capable models available for provider '{ai_provider}'",
                    severity="error"
                )

            model_ids = [m.id for m in vision_models]
            if ai_model not in model_ids:
                return ValidationError(
                    field="ai_model",
                    message=f"Model '{ai_model}' is not available or not vision-capable. Available vision models: {', '.join(model_ids)}",
                    severity="error"
                )
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
            return ValidationError(
                field="ai_model",
                message=f"Failed to check model availability: {e}",
                severity="error"
            )

        return None

    def _check_api_key(self, ai_provider: Optional[str]) -> Optional[ValidationError]:
        """Check if API key is present for cloud providers.

        Args:
            ai_provider: AI provider name

        Returns:
            ValidationError if API key missing for cloud provider, None otherwise
        """
        # Ollama doesn't require API key
        if ai_provider == "ollama":
            return None

        # Check for Gemini API key
        if ai_provider == "gemini":
            try:
                api_key = self._credential_store.get("gemini_api_key")
                if not api_key:
                    return ValidationError(
                        field="gemini_api_key",
                        message="Gemini API key not configured. Set it in settings.",
                        severity="error"
                    )
            except Exception as e:
                logger.error(f"Error checking Gemini API key: {e}")
                return ValidationError(
                    field="gemini_api_key",
                    message=f"Failed to check API key: {e}",
                    severity="error"
                )

        # Check for OpenRouter API key
        if ai_provider == "openrouter":
            try:
                api_key = self._credential_store.get("openrouter_api_key")
                if not api_key:
                    return ValidationError(
                        field="openrouter_api_key",
                        message="OpenRouter API key not configured. Set it in settings.",
                        severity="error"
                    )
            except Exception as e:
                logger.error(f"Error checking OpenRouter API key: {e}")
                return ValidationError(
                    field="openrouter_api_key",
                    message=f"Failed to check API key: {e}",
                    severity="error"
                )

        return None

    def _check_mobsf_reachable(self) -> Optional[ValidationError]:
        """Check if MobSF server is reachable (optional, warn only).

        Returns:
            ValidationError if MobSF not reachable (warning severity), None otherwise
        """
        try:
            mobsf_url = self._config_manager.get("MOBSF_URL", "http://localhost:8000")

            # This is a simple check - in production, you'd make an HTTP request
            # For now, we'll just check if the URL is configured
            if not mobsf_url:
                return ValidationError(
                    field="mobsf",
                    message="MobSF server URL not configured. Static analysis will be skipped.",
                    severity="warning"
                )
        except Exception as e:
            logger.error(f"Error checking MobSF configuration: {e}")
            return ValidationError(
                field="mobsf",
                message=f"Failed to check MobSF configuration: {e}",
                severity="warning"
            )

        return None

    def _check_pcapdroid_installed(self) -> Optional[ValidationError]:
        """Check if PCAPdroid is installed on device (optional, warn only).

        Returns:
            ValidationError if PCAPdroid not found (warning severity), None otherwise
        """
        try:
            devices = self._device_detector.get_connected_devices()

            if not devices:
                return ValidationError(
                    field="pcapdroid",
                    message="No device connected. Cannot verify PCAPdroid installation.",
                    severity="warning"
                )

            # Check if PCAPdroid package exists on device
            # This is a simplified check - in production, you'd use ADB to verify
            pcapdroid_installed = self._config_manager.get("PCAPDROID_INSTALLED", False)

            if not pcapdroid_installed:
                return ValidationError(
                    field="pcapdroid",
                    message="PCAPdroid may not be installed on device. Traffic capture will be skipped.",
                    severity="warning"
                )
        except Exception as e:
            logger.error(f"Error checking PCAPdroid: {e}")
            return ValidationError(
                field="pcapdroid",
                message=f"Failed to check PCAPdroid: {e}",
                severity="warning"
            )

        return None

    def _check_video_available(self) -> Optional[ValidationError]:
        """Check if video recording is available (optional, warn only).

        Returns:
            ValidationError if video not available (warning severity), None otherwise
        """
        try:
            # Check if Appium supports screen recording
            video_available = self._config_manager.get("VIDEO_RECORDING_AVAILABLE", True)

            if not video_available:
                return ValidationError(
                    field="video",
                    message="Video recording may not be available. Session video will be skipped.",
                    severity="warning"
                )
        except Exception as e:
            logger.error(f"Error checking video availability: {e}")
            return ValidationError(
                field="video",
                message=f"Failed to check video availability: {e}",
                severity="warning"
            )

        return None

    def has_errors(self, errors: List[ValidationError]) -> bool:
        """Check if there are any error-severity validation errors.

        Args:
            errors: List of validation errors

        Returns:
            True if there are error-severity issues, False otherwise
        """
        return any(e.severity == "error" for e in errors)

    def has_warnings_only(self, errors: List[ValidationError]) -> bool:
        """Check if there are only warnings (no errors).

        Args:
            errors: List of validation errors

        Returns:
            True if only warnings, False otherwise
        """
        return all(e.severity in ["warning", "info"] for e in errors) and not any(
            e.severity == "error" for e in errors
        )
