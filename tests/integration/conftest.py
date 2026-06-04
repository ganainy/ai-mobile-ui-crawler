"""Integration test configuration and fixtures."""

import subprocess
from collections.abc import Generator
from pathlib import Path

import pytest

from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.infrastructure.device_detection import DeviceDetection


@pytest.fixture(scope="session")
def android_device() -> Generator[str, None, None]:
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
    try:
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

        pytest.skip("No Android devices available and emulator setup not configured")

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip("ADB not available or emulator not configured")


@pytest.fixture(scope="session")
def sample_app(tmp_path_factory) -> Generator[Path, None, None]:
    """Provide a sample APK for testing."""
    test_apk_path = Path(__file__).parent.parent / "test_apps" / "sample.apk"

    if not test_apk_path.exists():
        test_apps_dir = Path(__file__).parent.parent / "test_apps"
        test_apps_dir.mkdir(exist_ok=True)

        readme_path = test_apps_dir / "README.md"
        readme_content = """# Test Apps

This directory should contain APK files for integration testing.
"""
        readme_path.write_text(readme_content)

        pytest.skip(f"Sample APK not found at {test_apk_path}. See {readme_path} for setup instructions.")

    yield test_apk_path


@pytest.fixture
def test_config(tmp_path) -> Generator[ConfigManager, None, None]:
    """Create a test configuration manager with isolated storage."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

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
    result = subprocess.run(
        ["adb", "-s", android_device, "install", "-r", str(sample_app)],
        capture_output=True,
        text=True,
        timeout=60
    )

    if result.returncode != 0:
        pytest.skip(f"Failed to install test app: {result.stderr}")

    package_name = "com.example.testapp"

    yield package_name

    try:
        subprocess.run(
            ["adb", "-s", android_device, "uninstall", package_name],
            capture_output=True,
            timeout=30
        )
    except Exception:
        pass


# Auth test fixtures (skipped — device_verifier helpers not fully implemented)
@pytest.fixture
def auth_navigator():
    pytest.skip("auth_navigator fixture not implemented — e2e auth tests require device_verifier setup")


@pytest.fixture
def auth_form_filler():
    pytest.skip("auth_form_filler fixture not implemented — e2e auth tests require device_verifier setup")


@pytest.fixture
def auth_verifier():
    pytest.skip("auth_verifier fixture not implemented — e2e auth tests require device_verifier setup")
