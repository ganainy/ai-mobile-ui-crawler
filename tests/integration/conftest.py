"""Integration test configuration and fixtures."""

import os
import subprocess
import time
import pytest
import requests
from pathlib import Path
from typing import Generator, Optional

from mobile_crawler.infrastructure.appium_driver import AppiumDriver
from mobile_crawler.infrastructure.device_detection import DeviceDetection
from mobile_crawler.config.config_manager import ConfigManager


@pytest.fixture(scope="session")
def appium_server() -> Generator[str, None, None]:
    """Start Appium server for integration tests."""
    # Check if Appium is already running
    try:
        response = requests.get("http://localhost:4723/status", timeout=5)
        if response.status_code == 200:
            yield "http://localhost:4723"
            return
    except requests.RequestException:
        pass

    # Start Appium server using npx
    appium_process = subprocess.Popen(
        ["npx", "appium", "--address", "127.0.0.1", "--port", "4723", "--relaxed-security"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True  # Required on Windows
    )

    # Wait for server to start
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get("http://localhost:4723/status", timeout=5)
            if response.status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(1)
    else:
        appium_process.terminate()
        pytest.skip("Appium server failed to start")

    yield "http://localhost:4723"

    # Cleanup
    appium_process.terminate()
    appium_process.wait()


@pytest.fixture(scope="session")
def android_device(appium_server: str) -> Generator[str, None, None]:
    """Get an available Android device (real or emulator)."""
    detector = DeviceDetection()

    # First try to find real devices
    devices = detector.get_connected_devices()
    available_devices = [d for d in devices if d.is_available]
    if available_devices:
        device_id = available_devices[0].device_id
        yield device_id
        return

    # If no real devices, try to start an emulator
    # This is a simplified approach - in practice you'd want more sophisticated emulator management
    try:
        # Check if emulator is already running
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=10
        )

        running_devices = []
        for line in result.stdout.split('\n')[1:]:
            if line.strip() and not line.startswith('*'):
                parts = line.split()
                if len(parts) >= 2 and parts[1] == 'device':
                    running_devices.append(parts[0])

        if running_devices:
            yield running_devices[0]
            return

        # Try to start a default emulator
        # Note: This assumes 'emulator -avd <name>' works
        # In practice, you'd want to check available AVDs first
        pytest.skip("No Android devices available and emulator setup not configured")

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip("ADB not available or emulator not configured")


@pytest.fixture(scope="session")
def sample_app(tmp_path_factory) -> Generator[Path, None, None]:
    """Provide a sample APK for testing."""
    # For now, we'll create a placeholder that expects a test APK
    # In practice, you'd either:
    # 1. Download a known test APK
    # 2. Build a simple test app
    # 3. Use an existing sample app

    test_apk_path = Path(__file__).parent.parent / "test_apps" / "sample.apk"

    if not test_apk_path.exists():
        # Create test_apps directory and provide instructions
        test_apps_dir = Path(__file__).parent.parent / "test_apps"
        test_apps_dir.mkdir(exist_ok=True)

        readme_path = test_apps_dir / "README.md"
        readme_content = """# Test Apps

This directory should contain APK files for integration testing.

## Recommended Test Apps

1. **Simple Calculator App**: Basic arithmetic operations
2. **Note-taking App**: Text input, lists, navigation
3. **Weather App**: API calls, data display, settings

## Setup Instructions

1. Find or create a simple Android app
2. Build the APK (debug or release)
3. Place the APK file in this directory
4. Update the integration tests to use your app's package name

## Example Test App

You can create a simple test app using Android Studio or download sample apps from:
- https://github.com/android/testing-samples
- https://developer.android.com/training/basics/firstapp
"""
        readme_path.write_text(readme_content)

        pytest.skip(f"Sample APK not found at {test_apk_path}. See {readme_path} for setup instructions.")

    yield test_apk_path


@pytest.fixture
def appium_driver(android_device: str, appium_server: str) -> Generator[AppiumDriver, None, None]:
    """Create an Appium driver instance for testing."""
    driver = AppiumDriver(android_device)
    
    # Connect to Appium server
    driver.connect()
    
    yield driver

    # Cleanup
    try:
        driver.disconnect()
    except Exception:
        pass


@pytest.fixture
def test_config(tmp_path) -> Generator[ConfigManager, None, None]:
    """Create a test configuration manager with isolated storage."""
    # Create a temporary config directory
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Override the config paths to use temporary directory
    original_get_app_data_dir = None
    try:
        from mobile_crawler.config import paths
        original_get_app_data_dir = paths.get_app_data_dir
        paths.get_app_data_dir = lambda: config_dir

        config_manager = ConfigManager()
        config_manager.user_config_store.create_schema()

        yield config_manager

    finally:
        if original_get_app_data_dir:
            paths.get_app_data_dir = original_get_app_data_dir


@pytest.fixture
def installed_test_app(android_device: str, sample_app: Path) -> Generator[str, None, None]:
    """Install the test app on the device and return its package name."""
    # Install the APK
    result = subprocess.run(
        ["adb", "-s", android_device, "install", "-r", str(sample_app)],
        capture_output=True,
        text=True,
        timeout=60
    )

    if result.returncode != 0:
        pytest.skip(f"Failed to install test app: {result.stderr}")

    # Extract package name from APK (simplified - in practice you'd use aapt or similar)
    # For now, we'll use a placeholder package name
    # In a real implementation, you'd parse the APK or have it configured
    package_name = "com.example.testapp"  # Placeholder

    yield package_name

    # Uninstall after test
    try:
        subprocess.run(
            ["adb", "-s", android_device, "uninstall", package_name],
            capture_output=True,
            timeout=30
        )
    except Exception:
        pass

@pytest.fixture(scope="module")
def auth_device_session(android_device):
    """Fixture to manage the DeviceSession for auth tests."""
    from tests.integration.device_verifier.session import DeviceSession
    APP_PACKAGE = "com.example.auth_test_app"
    session = DeviceSession(
        device_id=android_device,
        # app_package=APP_PACKAGE  # We handle launch via deep links
    )
    session.connect()
    yield session
    session.disconnect()

@pytest.fixture(scope="module")
def auth_navigator(android_device):
    """Fixture for AuthNavigator."""
    from tests.integration.device_verifier.deep_link_navigator import DeepLinkNavigator
    from tests.integration.device_verifier.auth.auth_navigator import AuthNavigator
    APP_PACKAGE = "com.example.auth_test_app"
    deep_link_navigator = DeepLinkNavigator(
        device_id=android_device,
        app_package=APP_PACKAGE
    )
    return AuthNavigator(deep_link_navigator)

@pytest.fixture(scope="module")
def auth_verifier(auth_device_session):
    """Fixture for AuthVerifier."""
    from tests.integration.device_verifier.auth.auth_verifier import AuthVerifier
    return AuthVerifier(driver=auth_device_session.get_driver())

@pytest.fixture(scope="module")
def auth_form_filler(auth_device_session):
    """Fixture for AuthFormFiller."""
    from mobile_crawler.infrastructure.gesture_handler import GestureHandler
    from tests.integration.device_verifier.auth.auth_form_filler import AuthFormFiller
    
    class DriverWrapper:
        def __init__(self, driver):
            self.driver = driver
        def get_driver(self):
            return self.driver
            
    wrapper = DriverWrapper(auth_device_session.get_driver())
    gesture_handler = GestureHandler(wrapper)
    width, height = auth_device_session.get_screen_dimensions()
    return AuthFormFiller(gesture_handler, (width, height))


# ============================================================================
# Gmail Automation Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def gmail_config():
    """Fixture for Gmail automation configuration."""
    from tests.integration.device_verifier.gmail.gmail_configs import GmailAutomationConfig
    return GmailAutomationConfig(
        poll_interval_seconds=5,
        max_wait_seconds=60,
        capture_screenshots=True,
        screenshot_dir="gmail_failures"
    )


@pytest.fixture(scope="module")
def gmail_navigator(auth_device_session, android_device, gmail_config):
    """Fixture for GmailNavigator."""
    from tests.integration.device_verifier.gmail.gmail_navigator import GmailNavigator
    return GmailNavigator(
        driver=auth_device_session.get_driver(),
        device_id=android_device,
        config=gmail_config
    )


@pytest.fixture(scope="module")
def gmail_reader(auth_device_session, android_device, gmail_config):
    """Fixture for GmailReader."""
    from tests.integration.device_verifier.gmail.gmail_reader import GmailReader
    return GmailReader(
        driver=auth_device_session.get_driver(),
        device_id=android_device,
        config=gmail_config
    )


@pytest.fixture(scope="module")
def app_switcher(auth_device_session, android_device, gmail_config):
    """Fixture for AppSwitcher."""
    from tests.integration.device_verifier.gmail.app_switcher import AppSwitcher
    AUTH_APP_PACKAGE = "com.example.auth_test_app"
    return AppSwitcher(
        driver=auth_device_session.get_driver(),
        device_id=android_device,
        test_app_package=AUTH_APP_PACKAGE,
        config=gmail_config
    )


@pytest.fixture(scope="module")
def clipboard_helper(auth_device_session, android_device, gmail_config):
    """Fixture for ClipboardHelper."""
    from tests.integration.device_verifier.gmail.clipboard_helper import ClipboardHelper
    return ClipboardHelper(
        driver=auth_device_session.get_driver(),
        device_id=android_device,
        config=gmail_config
    )


@pytest.fixture(scope="module")
def gmail_auth_verifier(gmail_navigator, gmail_reader, app_switcher):
    """Fixture for GmailAuthVerifier."""
    from tests.integration.device_verifier.gmail.gmail_auth_verifier import GmailAuthVerifier
    return GmailAuthVerifier(
        navigator=gmail_navigator,
        reader=gmail_reader,
        switcher=app_switcher
    )


@pytest.fixture(scope="module")
def email_sender():
    """Fixture for mock EmailSender."""
    from tests.integration.device_verifier.gmail.email_sender import EmailSender
    return EmailSender(sender_email="afoda50@gmail.com")
