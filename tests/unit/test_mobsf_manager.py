"""Unit tests for MobSFManager timeout handling."""
import pytest
from unittest.mock import Mock, patch
from mobile_crawler.infrastructure.mobsf_manager import MobSFManager

class TestMobSFManagerTimeout:
    @pytest.fixture
    def config_manager(self):
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "mobsf_api_url": "http://localhost:8000",
            "mobsf_api_key": "test_key",
            "mobsf_request_timeout": 300,
            "enable_mobsf_analysis": True
        }.get(key, default)
        return config

    @pytest.fixture
    def manager(self, config_manager):
        return MobSFManager(config_manager=config_manager)

    @patch("requests.post")
    def test_make_api_request_uses_config_timeout(self, mock_post, manager, config_manager):
        """Test that _make_api_request uses the timeout from configuration."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response

        # Call with no explicit timeout
        manager._make_api_request("test", "POST")
        
        # Verify it used the default (300)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["timeout"] == 300

    @patch("requests.post")
    def test_make_api_request_uses_explicit_timeout(self, mock_post, manager):
        """Test that _make_api_request uses an explicit timeout if provided."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response

        # Call with explicit timeout
        manager._make_api_request("test", "POST", timeout=10)
        
        # Verify it used the explicit value
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["timeout"] == 10

    @patch("mobile_crawler.infrastructure.mobsf_manager.MobSFManager._make_api_request")
    def test_get_report_json_passes_timeout(self, mock_request, manager):
        """Test that get_report_json correctly passes the timeout."""
        mock_request.return_value = (True, {})
        
        manager.get_report_json("hash123", timeout=15)
        
        mock_request.assert_called_once_with("report_json", "POST", data={"hash": "hash123"}, timeout=15)

    @patch("mobile_crawler.infrastructure.mobsf_manager.MobSFManager.get_pdf_report")
    @patch("os.makedirs")
    @patch("builtins.open")
    def test_save_pdf_report_passes_timeout(self, mock_open, mock_makedirs, mock_get_pdf, manager):
        """Test that save_pdf_report correctly passes the timeout."""
        mock_get_pdf.return_value = (True, b"fake content")
        
        manager.save_pdf_report("hash123", output_path="/tmp/test.pdf", timeout=20)
        
        mock_get_pdf.assert_called_once_with("hash123", timeout=20)
