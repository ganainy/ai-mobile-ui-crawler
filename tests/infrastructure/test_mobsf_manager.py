"""Tests for MobSFManager."""

from unittest.mock import Mock, patch, MagicMock, mock_open
import pytest
import os
import tempfile

from mobile_crawler.infrastructure.mobsf_manager import (
    MobSFManager,
    MobSFConfig,
    MobSFAnalysisResult,
)


class TestMobSFConfig:
    """Tests for MobSFConfig dataclass."""

    def test_creation(self):
        """Test MobSFConfig creation."""
        config = MobSFConfig(
            enabled=True,
            api_url="http://localhost:8080",
            api_key="test_key",
        )

        assert config.enabled is True
        assert config.api_url == "http://localhost:8080"
        assert config.api_key == "test_key"

    def test_defaults(self):
        """Test MobSFConfig with defaults."""
        config = MobSFConfig(enabled=False)

        assert config.enabled is False
        assert config.api_url == "http://localhost:8000"
        assert config.api_key is None


class TestMobSFAnalysisResult:
    """Tests for MobSFAnalysisResult dataclass."""

    def test_creation(self):
        """Test MobSFAnalysisResult creation."""
        result = MobSFAnalysisResult(
            success=True,
            report_path="/path/to/report.pdf",
            json_path="/path/to/report.json",
            scan_id="abc123",
        )

        assert result.success is True
        assert result.report_path == "/path/to/report.pdf"
        assert result.json_path == "/path/to/report.json"
        assert result.scan_id == "abc123"
        assert result.error is None

    def test_creation_with_error(self):
        """Test MobSFAnalysisResult with error."""
        result = MobSFAnalysisResult(
            success=False,
            error="Analysis failed",
        )

        assert result.success is False
        assert result.error == "Analysis failed"
        assert result.report_path is None
        assert result.json_path is None
        assert result.scan_id is None


class TestMobSFManager:
    """Tests for MobSFManager."""

    def test_init(self):
        """Test initialization."""
        adb_client = Mock()
        config = MobSFConfig(enabled=True)
        manager = MobSFManager(adb_client=adb_client, config=config)

        assert manager._adb_client is adb_client
        assert manager._config is config
        assert manager._session_folder_manager is None

    def test_init_with_defaults(self):
        """Test initialization with default config."""
        manager = MobSFManager()

        assert manager._adb_client is None
        assert manager._config.enabled is False
        assert manager._session_folder_manager is None

    def test_configure(self):
        """Test configure method."""
        config = MobSFConfig(enabled=True, api_url="http://test.com")
        manager = MobSFManager()

        manager.configure(config)

        assert manager._config is config

    def test_set_session_folder_manager(self):
        """Test setting session folder manager."""
        manager = MobSFManager()
        session_manager = Mock()

        manager.set_session_folder_manager(session_manager)

        assert manager._session_folder_manager is session_manager

    def test_analyze_disabled(self):
        """Test analyze when MobSF is disabled."""
        config = MobSFConfig(enabled=False)
        manager = MobSFManager(config=config)

        result = manager.analyze("com.example.app", "device123")

        assert result.success is False
        assert "disabled" in result.error.lower()

    def test_analyze_no_api_key(self):
        """Test analyze when API key is not configured."""
        config = MobSFConfig(enabled=True, api_key=None)
        manager = MobSFManager(config=config)

        result = manager.analyze("com.example.app", "device123")

        assert result.success is False
        assert "api key" in result.error.lower()

    @patch("os.unlink")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake apk data")
    @patch("requests.post")
    @patch("tempfile.gettempdir")
    def test_analyze_success(
        self,
        mock_gettempdir,
        mock_post,
        mock_file_open,
        mock_exists,
        mock_unlink
    ):
        """Test successful analysis."""
        mock_gettempdir.return_value = "/tmp"
        mock_exists.return_value = True

        # Mock ADB responses
        adb_client = Mock()
        adb_client.execute.side_effect = [
            "package:/data/app/com.example.app/base.apk",  # pm path
            "",  # pull command (empty stdout means success)
        ]

        # Mock MobSF responses
        upload_response = Mock()
        upload_response.status_code = 200
        upload_response.json.return_value = {"hash": "scan123"}
        
        pdf_response = Mock()
        pdf_response.status_code = 200
        pdf_response.content = b"fake pdf content"
        
        json_response = Mock()
        json_response.status_code = 200
        json_response.text = '{"fake": "json"}'
        
        mock_post.side_effect = [upload_response, pdf_response, json_response]

        config = MobSFConfig(enabled=True, api_key="test_key")
        manager = MobSFManager(adb_client=adb_client, config=config)

        result = manager.analyze("com.example.app", "device123")

        assert result.success is True
        assert result.scan_id == "scan123"
        # Reports should be downloaded to temp dir
        assert result.report_path == "/tmp\\com.example.app_mobsf_report.pdf"
        assert result.json_path == "/tmp\\com.example.app_mobsf_report.json"

    @patch("os.unlink")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake apk data")
    @patch("requests.post")
    @patch("tempfile.gettempdir")
    def test_analyze_upload_failure(
        self,
        mock_gettempdir,
        mock_post,
        mock_file_open,
        mock_exists,
        mock_unlink
    ):
        """Test analyze when upload fails."""
        mock_gettempdir.return_value = "/tmp"
        mock_exists.return_value = True

        # Mock ADB responses
        adb_client = Mock()
        adb_client.execute.side_effect = [
            "package:/data/app/com.example.app/base.apk",
            "",
        ]

        # Mock MobSF upload failure
        upload_response = Mock()
        upload_response.status_code = 500
        mock_post.return_value = upload_response

        config = MobSFConfig(enabled=True, api_key="test_key")
        manager = MobSFManager(adb_client=adb_client, config=config)

        result = manager.analyze("com.example.app", "device123")

        assert result.success is False
        assert "upload" in result.error.lower()

    @patch("os.unlink")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake apk data")
    @patch("requests.post")
    @patch("tempfile.gettempdir")
    def test_analyze_extract_apk_failure(
        self,
        mock_gettempdir,
        mock_post,
        mock_file_open,
        mock_exists,
        mock_unlink
    ):
        """Test analyze when APK extraction fails."""
        mock_gettempdir.return_value = "/tmp"
        mock_exists.return_value = True

        # Mock ADB failure
        adb_client = Mock()
        adb_client.execute.return_value = None

        config = MobSFConfig(enabled=True, api_key="test_key")
        manager = MobSFManager(adb_client=adb_client, config=config)

        result = manager.analyze("com.example.app", "device123")

        assert result.success is False
        assert "extract" in result.error.lower()

    @patch("os.unlink")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake apk data")
    @patch("requests.post")
    @patch("tempfile.gettempdir")
    def test_analyze_package_not_found(
        self,
        mock_gettempdir,
        mock_post,
        mock_file_open,
        mock_exists,
        mock_unlink
    ):
        """Test analyze when package is not found on device."""
        mock_gettempdir.return_value = "/tmp"
        mock_exists.return_value = True

        # Mock ADB response - package not found
        adb_client = Mock()
        adb_client.execute.return_value = "package not found"

        config = MobSFConfig(enabled=True, api_key="test_key")
        manager = MobSFManager(adb_client=adb_client, config=config)

        result = manager.analyze("com.example.app", "device123")

        assert result.success is False
        assert "package" in result.error.lower()

    def test_analyze_run_no_session_manager(self):
        """Test analyze_run when session folder manager is not configured."""
        config = MobSFConfig(enabled=True, api_key="test_key")
        manager = MobSFManager(config=config)

        result = manager.analyze_run(1, "com.example.app", "device123")

        assert result.success is False
        assert "session folder manager" in result.error.lower()

    @patch("os.unlink")
    @patch("os.rename")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake apk data")
    @patch("requests.post")
    @patch("tempfile.gettempdir")
    def test_analyze_run_success(
        self,
        mock_gettempdir,
        mock_post,
        mock_file_open,
        mock_exists,
        mock_rename,
        mock_unlink
    ):
        """Test analyze_run with successful analysis."""
        mock_gettempdir.return_value = "/tmp"
        mock_exists.return_value = True

        # Mock ADB responses
        adb_client = Mock()
        adb_client.execute.side_effect = [
            "package:/data/app/com.example.app/base.apk",
            "",
        ]

        # Mock MobSF upload response
        upload_response = Mock()
        upload_response.status_code = 200
        upload_response.json.return_value = {"hash": "scan123"}
        mock_post.return_value = upload_response

        # Mock session folder manager
        session_manager = Mock()
        session_manager.get_session_folder.return_value = "/session/folder"

        config = MobSFConfig(enabled=True, api_key="test_key")
        manager = MobSFManager(adb_client=adb_client, config=config)
        manager.set_session_folder_manager(session_manager)

        result = manager.analyze_run(1, "com.example.app", "device123")

        assert result.success is True
        assert result.scan_id == "scan123"

    def test_is_available_disabled(self):
        """Test is_available when MobSF is disabled."""
        config = MobSFConfig(enabled=False)
        manager = MobSFManager(config=config)

        assert manager.is_available() is False

    def test_is_available_no_api_key(self):
        """Test is_available when API key is not configured."""
        config = MobSFConfig(enabled=True, api_key=None)
        manager = MobSFManager(config=config)

        assert manager.is_available() is False

    @patch("requests.get")
    def test_is_available_success(self, mock_get):
        """Test is_available when MobSF is reachable."""
        response = Mock()
        response.status_code = 200
        mock_get.return_value = response

        config = MobSFConfig(enabled=True, api_key="test_key")
        manager = MobSFManager(config=config)

        assert manager.is_available() is True

    @patch("requests.get")
    def test_is_available_failure(self, mock_get):
        """Test is_available when MobSF is not reachable."""
        mock_get.side_effect = Exception("Connection error")

        config = MobSFConfig(enabled=True, api_key="test_key")
        manager = MobSFManager(config=config)

        assert manager.is_available() is False

    def test_get_config(self):
        """Test get_config method."""
        config = MobSFConfig(enabled=True, api_url="http://test.com")
        manager = MobSFManager(config=config)

        result = manager.get_config()

        assert result is config

    @patch("os.unlink")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake apk data")
    @patch("requests.post")
    @patch("tempfile.gettempdir")
    def test_execute_adb_command_with_client(
        self,
        mock_gettempdir,
        mock_post,
        mock_file_open,
        mock_exists,
        mock_unlink
    ):
        """Test _execute_adb_command uses ADB client when available."""
        adb_client = Mock()
        adb_client.execute.return_value = "test_output"
        manager = MobSFManager(adb_client=adb_client)

        result = manager._execute_adb_command("shell test")

        assert result == "test_output"
        adb_client.execute.assert_called_once_with("shell test")

    @patch("subprocess.run")
    def test_execute_adb_command_without_client(self, mock_run):
        """Test _execute_adb_command falls back to subprocess when no client."""
        from subprocess import CompletedProcess
        mock_run.return_value = CompletedProcess(
            args=["adb", "shell", "test"],
            returncode=0,
            stdout="test_output"
        )
        manager = MobSFManager()

        result = manager._execute_adb_command("shell test")

        assert result == "test_output"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_execute_adb_command_timeout(self, mock_run):
        """Test _execute_adb_command handles timeout."""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("adb", 30)
        manager = MobSFManager()

        result = manager._execute_adb_command("shell test")

        assert result is None

    @patch("subprocess.run")
    def test_execute_adb_command_file_not_found(self, mock_run):
        """Test _execute_adb_command handles ADB not found."""
        mock_run.side_effect = FileNotFoundError()
        manager = MobSFManager()

        result = manager._execute_adb_command("shell test")

        assert result is None

    @patch("requests.post")
    def test_upload_to_mobsf_no_requests(self, mock_post):
        """Test _upload_to_mobsf when requests library is not available."""
        mock_post.side_effect = ImportError("requests not available")

        manager = MobSFManager()
        manager.configure(MobSFConfig(enabled=True, api_key="test_key"))

        result = manager._upload_to_mobsf("/tmp/test.apk")

        assert result is None

    @patch("requests.post")
    def test_upload_to_mobsf_missing_scan_id(self, mock_post):
        """Test _upload_to_mobsf when response is missing scan ID."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {}
        mock_post.return_value = response

        manager = MobSFManager()
        manager.configure(MobSFConfig(enabled=True, api_key="test_key"))

        result = manager._upload_to_mobsf("/tmp/test.apk")

        assert result is None
