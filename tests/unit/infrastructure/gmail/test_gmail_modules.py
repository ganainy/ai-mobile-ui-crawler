"""
Unit tests for Gmail infrastructure modules.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from mobile_crawler.infrastructure.gmail.config import GmailSearchQuery, OTP_PATTERNS
from mobile_crawler.infrastructure.gmail.reader import GmailReader, OTPResult
from mobile_crawler.infrastructure.gmail.navigator import GmailNavigator
from mobile_crawler.infrastructure.gmail.app_switcher import AppSwitcher

class TestGmailConfig:
    def test_gmail_search_query_builder(self):
        query = GmailSearchQuery(
            sender="test@example.com",
            subject_contains="Verification",
            is_unread=True
        )
        query_str = query.to_gmail_query()
        assert "from:test@example.com" in query_str
        assert "subject:Verification" in query_str
        assert "is:unread" in query_str

    def test_otp_patterns(self):
        import re
        text = "Your code is 123456"
        matched = False
        for pattern in OTP_PATTERNS:
            if re.search(pattern, text):
                matched = True
                break
        assert matched

class TestGmailReader:
    @pytest.fixture
    def mock_driver(self):
        return MagicMock()

    def test_extract_otp_success(self, mock_driver):
        reader = GmailReader(mock_driver)
        reader.get_email_content = MagicMock(return_value="Your verification code is: 123456")
        
        result = reader.extract_otp()
        
        assert result is not None
        assert result.code == "123456"

    def test_extract_otp_not_found(self, mock_driver):
        reader = GmailReader(mock_driver)
        reader.get_email_content = MagicMock(return_value="Hello, how are you?")
        
        result = reader.extract_otp()
        
        assert result is None

class TestAppSwitcher:
    @pytest.fixture
    def mock_driver(self):
        driver = MagicMock()
        driver.current_package = "com.google.android.gm"
        return driver

    def test_is_gmail_foreground(self, mock_driver):
        switcher = AppSwitcher(mock_driver, "device_id", "com.test.app")
        assert switcher.is_gmail_foreground() is True
        
        mock_driver.current_package = "com.test.app"
        assert switcher.is_gmail_foreground() is False

class TestGmailNavigator:
    @pytest.fixture
    def mock_driver(self):
        return MagicMock()

    def test_ensure_correct_account_already_active(self, mock_driver):
        from mobile_crawler.infrastructure.gmail.config import GmailAutomationConfig
        config = GmailAutomationConfig(target_account="target@gmail.com")
        navigator = GmailNavigator(mock_driver, "device_id", config)
        
        # Mock profile button with correct account in content-desc
        mock_profile_btn = MagicMock()
        mock_profile_btn.get_attribute.return_value = "Google Account: Target (target@gmail.com)"
        
        with patch("mobile_crawler.infrastructure.gmail.navigator.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.return_value = mock_profile_btn
            
            result = navigator.ensure_correct_account()
            
            assert result is True
            mock_profile_btn.click.assert_not_called()

    def test_ensure_correct_account_switch_success(self, mock_driver):
        from mobile_crawler.infrastructure.gmail.config import GmailAutomationConfig
        config = GmailAutomationConfig(target_account="target@gmail.com")
        navigator = GmailNavigator(mock_driver, "device_id", config)
        
        # Current account mismatch
        mock_profile_btn = MagicMock()
        mock_profile_btn.get_attribute.side_effect = [
            "Google Account: Other (other@gmail.com)", # first call
            "Google Account: Target (target@gmail.com)"  # verification call
        ]
        
        mock_target_item = MagicMock()
        
        with patch("mobile_crawler.infrastructure.gmail.navigator.WebDriverWait") as mock_wait:
            # First wait for profile button
            # Second wait for target account item
            # Third wait for profile button verification
            mock_wait.return_value.until.side_effect = [
                mock_profile_btn, 
                mock_target_item, 
                mock_profile_btn
            ]
            
            result = navigator.ensure_correct_account()
            
            assert result is True
            mock_profile_btn.click.assert_called_once()
            mock_target_item.click.assert_called_once()
