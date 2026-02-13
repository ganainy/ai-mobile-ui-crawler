import pytest
from unittest.mock import MagicMock, patch
from mobile_crawler.domain.action_executor import ActionExecutor
from mobile_crawler.domain.models import ActionResult

@pytest.fixture
def mock_appium_driver():
    driver = MagicMock()
    driver.device_id = "test-device"
    return driver

@pytest.fixture
def mock_gesture_handler():
    return MagicMock()

@pytest.fixture
def mock_mailosaur_service():
    return MagicMock()

@pytest.fixture
def action_executor(mock_appium_driver, mock_gesture_handler, mock_mailosaur_service):
    return ActionExecutor(
        appium_driver=mock_appium_driver,
        gesture_handler=mock_gesture_handler,
        mailosaur_service=mock_mailosaur_service,
        test_email="test@example.com"
    )

def test_extract_otp_success(action_executor, mock_mailosaur_service):
    # Setup
    mock_mailosaur_service.get_otp.return_value = "123456"
    
    # Execute
    result = action_executor.extract_otp(email="user@mailosaur.io")
    
    # Verify
    assert result.success is True
    assert result.input_text == "123456"
    assert "Mailosaur (user@mailosaur.io)" in result.target
    mock_mailosaur_service.get_otp.assert_called_once_with("user@mailosaur.io", timeout=60)

def test_extract_otp_fallback_email(action_executor, mock_mailosaur_service):
    # Setup
    mock_mailosaur_service.get_otp.return_value = "123456"
    
    # Execute (no email provided)
    result = action_executor.extract_otp()
    
    # Verify
    assert result.success is True
    mock_mailosaur_service.get_otp.assert_called_once_with("test@example.com", timeout=60)

def test_extract_otp_not_found(action_executor, mock_mailosaur_service):
    # Setup
    mock_mailosaur_service.get_otp.return_value = None
    
    # Execute
    result = action_executor.extract_otp()
    
    # Verify
    assert result.success is False
    assert "found" in result.error_message

def test_click_verification_link_success(action_executor, mock_mailosaur_service):
    # Setup
    mock_mailosaur_service.get_magic_link.return_value = "https://example.com/verify"
    
    with patch.object(action_executor, '_open_url_via_adb') as mock_adb:
        # Execute
        result = action_executor.click_verification_link(email="user@mailosaur.io", link_text="Verify")
        
        # Verify
        assert result.success is True
        mock_mailosaur_service.get_magic_link.assert_called_once_with("user@mailosaur.io", "Verify", timeout=60)
        mock_adb.assert_called_once_with("https://example.com/verify")

def test_click_verification_link_not_found(action_executor, mock_mailosaur_service):
    # Setup
    mock_mailosaur_service.get_magic_link.return_value = None
    
    # Execute
    result = action_executor.click_verification_link()
    
    # Verify
    assert result.success is False
    assert "found" in result.error_message

def test_mailosaur_not_configured(mock_appium_driver, mock_gesture_handler):
    # Setup without mailosaur_service
    executor = ActionExecutor(mock_appium_driver, mock_gesture_handler)
    
    # Execute
    result = executor.extract_otp()
    
    # Verify
    assert result.success is False
    assert "not configured" in result.error_message
