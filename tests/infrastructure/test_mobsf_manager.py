"""Tests for MobSFManager."""

import os
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from mobile_crawler.infrastructure.mobsf_manager import (
    MOBSF_INVALID_KEY_ERROR,
    MOBSF_KEY_DISCOVERY_ERROR,
    MobSFAnalysisResult,
    MobSFManager,
)


def _make_config_manager(**overrides):
    """Create a mock ConfigManager with MobSF defaults."""
    defaults = {
        "mobsf_api_key": "test_key",
        "mobsf_api_url": "http://localhost:8000",
        "enable_mobsf_analysis": True,
        "mobsf_request_timeout": 300,
        "mobsf_scan_timeout": 900,
        "mobsf_poll_interval": 2,
        "adb_executable_path": "adb",
    }
    defaults.update(overrides)
    config = Mock()
    config.get.side_effect = lambda key, default=None: defaults.get(key, default)
    return config


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
        config = _make_config_manager()
        adb_client = Mock()
        manager = MobSFManager(config_manager=config, adb_client=adb_client)

        assert manager.config_manager is config
        assert manager.adb_client is adb_client
        assert manager.session_folder_manager is None

    def test_init_with_defaults(self):
        """Test initialization with default config."""
        config = _make_config_manager()
        manager = MobSFManager(config_manager=config)

        assert manager.adb_client is None
        assert manager.session_folder_manager is None

    def test_init_raises_without_api_url(self):
        """Test initialization raises when api_url is empty."""
        config = _make_config_manager(mobsf_api_url="")
        with pytest.raises(ValueError, match="MOBSF_API_URL must be set"):
            MobSFManager(config_manager=config)

    def test_analyze_disabled(self):
        """Test analyze_run when MobSF is disabled."""
        config = _make_config_manager(enable_mobsf_analysis=False)
        manager = MobSFManager(config_manager=config)

        run = Mock()
        run.app_package = "com.example.app"
        run.id = 1
        result = manager.analyze_run(run, "device123")

        assert result.success is False
        assert "disabled" in result.error.lower()

    def test_perform_complete_scan_fails_without_api_key(self):
        """Missing MobSF API keys should fail clearly before ADB/API work."""
        config = _make_config_manager(mobsf_api_key=None)
        manager = MobSFManager(config_manager=config)
        manager._find_api_key_file = Mock(return_value=None)
        manager._discover_api_key_from_docker_logs = Mock(return_value="")

        success, summary = manager.perform_complete_scan("com.example.app")

        assert success is False
        assert summary["error"] == MOBSF_KEY_DISCOVERY_ERROR

    @patch.object(MobSFManager, "perform_complete_scan")
    def test_analyze_run_with_perform_complete_scan_failure(self, mock_perform):
        """Test analyze_run wraps perform_complete_scan failure."""
        mock_perform.return_value = (False, {"error": "Scan failed"})

        config = _make_config_manager()
        manager = MobSFManager(config_manager=config)

        run = Mock()
        run.app_package = "com.example.app"
        run.id = 1
        run.session_path = "/tmp/session"
        result = manager.analyze_run(run, "device123")

        assert result.success is False
        assert "scan failed" in result.error.lower()

    @patch.object(MobSFManager, "perform_complete_scan")
    def test_analyze_run_with_perform_complete_scan_success(self, mock_perform):
        """Test analyze_run wraps perform_complete_scan success."""
        mock_perform.return_value = (True, {
            "pdf_report": "/tmp/report.pdf",
            "json_report": "/tmp/report.json",
            "file_hash": "abc123",
            "security_score": {"score": 90},
        })

        config = _make_config_manager()
        manager = MobSFManager(config_manager=config)

        run = Mock()
        run.app_package = "com.example.app"
        run.id = 1
        run.session_path = "/tmp/session"
        result = manager.analyze_run(run, "device123")

        assert result.success is True
        assert result.scan_id == "abc123"
        assert result.report_path == "/tmp/report.pdf"
        assert result.json_path == "/tmp/report.json"

    @patch.object(MobSFManager, "preflight", return_value=(True, ""))
    @patch("os.unlink")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake apk data")
    @patch("tempfile.gettempdir")
    @patch("subprocess.run")
    @patch("time.sleep")
    def test_perform_complete_scan_success(
        self,
        mock_sleep,
        mock_subprocess,
        mock_gettempdir,
        mock_file_open,
        mock_exists,
        mock_unlink,
        mock_preflight,
    ):
        """Test successful complete scan."""
        mock_gettempdir.return_value = "/tmp"
        mock_exists.return_value = True

        # Mock ADB responses
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="package:/data/app/com.example.app/base.apk\n",
            stderr=""
        )

        config = _make_config_manager()
        manager = MobSFManager(config_manager=config)

        # Mock _make_api_request to avoid actual HTTP calls and polling loop
        def mock_api_request(endpoint, method="GET", data=None, files=None, stream=False, timeout=None):
            if endpoint == "upload":
                return True, {"hash": "scan123"}
            elif endpoint == "scan":
                return True, {"status": "ok"}
            elif endpoint == "scan_logs":
                return True, {"logs": [{"status": "Completed", "message": "Done", "timestamp": "2024-01-01T00:00:00"}]}
            elif endpoint == "report_json":
                return True, {"security_score": 80}
            elif endpoint == "download_pdf":
                return True, b"fake pdf"
            elif endpoint == "scorecard":
                return True, {"score": 85}
            return True, {}

        manager._make_api_request = Mock(side_effect=mock_api_request)

        with tempfile.TemporaryDirectory() as tmpdir:
            success, summary = manager.perform_complete_scan(
                package_name="com.example.app",
                session_path=tmpdir,
            )

        assert success is True
        assert summary["file_hash"] == "scan123"

    @patch("subprocess.run")
    def test_extract_apk_from_device_success(self, mock_subprocess):
        """Test extracting APK from device."""
        mock_subprocess.side_effect = [
            Mock(returncode=0, stdout="package:/data/app/com.example.app/base.apk\n", stderr=""),
            Mock(returncode=0, stdout="", stderr=""),
        ]

        config = _make_config_manager()
        manager = MobSFManager(config_manager=config)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = manager.extract_apk_from_device("com.example.app", output_dir=tmpdir)

        assert result is not None
        assert result.endswith("com.example.app.apk")

    @patch("subprocess.run")
    def test_extract_apk_uses_configured_adb_and_device(self, mock_subprocess):
        """APK extraction should target the run device with configured ADB."""
        mock_subprocess.side_effect = [
            Mock(returncode=0, stdout="package:/data/app/com.example.app/base.apk\n", stderr=""),
            Mock(returncode=0, stdout="", stderr=""),
        ]

        config = _make_config_manager(adb_executable_path="C:/Android/platform-tools/adb.exe")
        manager = MobSFManager(config_manager=config)

        with tempfile.TemporaryDirectory() as tmpdir:
            manager.extract_apk_from_device(
                "com.example.app",
                output_dir=tmpdir,
                device_id="emulator-5554",
            )

        first_cmd = mock_subprocess.call_args_list[0].args[0]
        second_cmd = mock_subprocess.call_args_list[1].args[0]
        assert first_cmd[:3] == ["C:/Android/platform-tools/adb.exe", "-s", "emulator-5554"]
        assert second_cmd[:3] == ["C:/Android/platform-tools/adb.exe", "-s", "emulator-5554"]

    @patch("subprocess.run")
    def test_extract_split_apks_packages_archive(self, mock_subprocess, tmp_path):
        """Split APK installs should be pulled and zipped as .apks."""
        remote_paths = (
            "package:/data/app/com.example.app/base.apk\n"
            "package:/data/app/com.example.app/split_config.en.apk\n"
        )

        def run_side_effect(command, **kwargs):
            if "pm" in command:
                return Mock(returncode=0, stdout=remote_paths, stderr="")
            local_path = Path(command[-1])
            local_path.write_bytes(b"apk")
            return Mock(returncode=0, stdout="", stderr="")

        mock_subprocess.side_effect = run_side_effect
        config = _make_config_manager()
        manager = MobSFManager(config_manager=config)

        archive_path = manager.extract_apk_from_device(
            "com.example.app",
            output_dir=str(tmp_path),
            device_id="device123",
        )

        assert archive_path.endswith("com.example.app.apks")
        with zipfile.ZipFile(archive_path) as archive:
            assert len(archive.namelist()) == 2

    @patch("subprocess.run")
    def test_extract_apk_from_device_failure(self, mock_subprocess):
        """Test extracting APK when pm path fails."""
        mock_subprocess.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Error"
        )

        config = _make_config_manager()
        manager = MobSFManager(config_manager=config)

        result = manager.extract_apk_from_device("com.example.app")

        assert result is None

    def test_upload_apk_file_not_found(self):
        """Test upload when APK file doesn't exist."""
        config = _make_config_manager()
        manager = MobSFManager(config_manager=config)

        success, result = manager.upload_apk("/nonexistent/path.apk")

        assert success is False
        assert "not found" in result.get("error", "").lower()

    @patch("requests.post")
    def test_upload_apk_success(self, mock_post):
        """Test successful APK upload."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"hash": "abc123", "status": "ok"}
        mock_post.return_value = mock_response

        config = _make_config_manager()
        manager = MobSFManager(config_manager=config)

        with tempfile.NamedTemporaryFile(suffix=".apk", delete=False) as tmp:
            tmp.write(b"fake apk")
            tmp_path = tmp.name

        try:
            success, result = manager.upload_apk(tmp_path)
            assert success is True
            assert result["hash"] == "abc123"
        finally:
            os.unlink(tmp_path)

    @patch("requests.post")
    def test_api_request_uses_authorization_header(self, mock_post, tmp_path, monkeypatch):
        """MobSF requests should include the resolved API key."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"status": "ok"}
        mock_post.return_value = mock_response

        (tmp_path / ".mobsf_api_key").write_text("runtime_key\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        config = _make_config_manager(mobsf_api_key=None)
        manager = MobSFManager(config_manager=config)

        success, _ = manager._make_api_request("upload", "POST")

        assert success is True
        assert mock_post.call_args.kwargs["headers"]["Authorization"] == "runtime_key"

    @patch("requests.post")
    def test_api_request_reads_key_at_execution_time(self, mock_post, tmp_path, monkeypatch):
        """Key file changes after construction should be honored."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"status": "ok"}
        mock_post.return_value = mock_response

        (tmp_path / ".mobsf_api_key").write_text("old_key\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        config = _make_config_manager(mobsf_api_key=None)
        manager = MobSFManager(config_manager=config)
        (tmp_path / ".mobsf_api_key").write_text("new_key\n", encoding="utf-8")

        manager._make_api_request("scan", "POST")

        assert mock_post.call_args.kwargs["headers"]["Authorization"] == "new_key"

    @patch("requests.post")
    def test_api_request_reads_key_file_fallback(self, mock_post, tmp_path, monkeypatch):
        """A repo-root .mobsf_api_key should be used when config is empty."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"status": "ok"}
        mock_post.return_value = mock_response
        (tmp_path / ".mobsf_api_key").write_text("file_key\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        config = _make_config_manager(mobsf_api_key=None)
        manager = MobSFManager(config_manager=config)

        manager._make_api_request("scan", "POST")

        assert mock_post.call_args.kwargs["headers"]["Authorization"] == "file_key"

    @patch("subprocess.run")
    def test_resolve_api_key_extracts_from_docker_logs(self, mock_run, tmp_path, monkeypatch):
        """Docker logs are used when .mobsf_api_key is missing."""
        docker_key = "0123456789abcdef0123456789abcdef"
        mock_run.return_value = Mock(
            returncode=0,
            stdout=f"REST API Key: {docker_key}\n",
            stderr="",
        )
        monkeypatch.chdir(tmp_path)
        config = _make_config_manager(mobsf_api_key=None)
        manager = MobSFManager(config_manager=config)

        assert manager._resolve_api_key() == docker_key
        assert (tmp_path / ".mobsf_api_key").read_text(encoding="utf-8").strip() == docker_key

    @patch("requests.get")
    def test_preflight_uses_existing_key_file(self, mock_get, tmp_path, monkeypatch):
        """An existing .mobsf_api_key is validated against an authenticated API route."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        (tmp_path / ".mobsf_api_key").write_text("file_key\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        config = _make_config_manager(mobsf_api_key=None)
        manager = MobSFManager(config_manager=config)

        success, error = manager.preflight()

        assert success is True
        assert error == ""
        assert mock_get.call_args.args[0] == "http://localhost:8000/api/v1/scans"
        assert mock_get.call_args.kwargs["headers"]["Authorization"] == "file_key"

    @patch("requests.get")
    def test_preflight_refreshes_stale_key_after_401(self, mock_get, tmp_path, monkeypatch):
        """A stale cached key is refreshed from Docker logs once after 401."""
        old_response = Mock()
        old_response.status_code = 401
        new_response = Mock()
        new_response.status_code = 200
        mock_get.side_effect = [old_response, new_response]
        (tmp_path / ".mobsf_api_key").write_text("old_key\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        config = _make_config_manager(mobsf_api_key=None)
        manager = MobSFManager(config_manager=config)
        manager._discover_api_key_from_docker_logs = Mock(return_value="abcdefabcdefabcdef")

        success, error = manager.preflight()

        assert success is True
        assert error == ""
        assert (tmp_path / ".mobsf_api_key").read_text(encoding="utf-8").strip() == "abcdefabcdefabcdef"
        assert mock_get.call_args_list[1].kwargs["headers"]["Authorization"] == "abcdefabcdefabcdef"

    @patch("requests.get")
    def test_preflight_fails_when_refreshed_key_is_invalid(self, mock_get, tmp_path, monkeypatch):
        """401 after Docker refresh fails with the invalid-key setup error."""
        first_response = Mock()
        first_response.status_code = 401
        second_response = Mock()
        second_response.status_code = 401
        mock_get.side_effect = [first_response, second_response]
        (tmp_path / ".mobsf_api_key").write_text("old_key\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        config = _make_config_manager(mobsf_api_key=None)
        manager = MobSFManager(config_manager=config)
        manager._discover_api_key_from_docker_logs = Mock(return_value="abcdefabcdefabcdef")

        success, error = manager.preflight()

        assert success is False
        assert error == MOBSF_INVALID_KEY_ERROR

    @patch.object(MobSFManager, "extract_apk_from_device")
    def test_perform_complete_scan_preflight_failure_skips_adb(self, mock_extract):
        """Preflight failure stops before APK extraction."""
        config = _make_config_manager()
        manager = MobSFManager(config_manager=config)
        manager.preflight = Mock(return_value=(False, MOBSF_INVALID_KEY_ERROR))

        success, summary = manager.perform_complete_scan("com.example.app")

        assert success is False
        assert summary["error"] == MOBSF_INVALID_KEY_ERROR
        mock_extract.assert_not_called()

    @patch("requests.post")
    def test_scan_apk_success(self, mock_post):
        """Test scanning uploaded APK."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_post.return_value = mock_response

        config = _make_config_manager()
        manager = MobSFManager(config_manager=config)

        success, result = manager.scan_apk("abc123")

        assert success is True

    @patch("requests.post")
    def test_get_report_json_success(self, mock_post):
        """Test getting JSON report."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"security_score": 80}
        mock_post.return_value = mock_response

        config = _make_config_manager()
        manager = MobSFManager(config_manager=config)

        success, result = manager.get_report_json("abc123")

        assert success is True
        assert result["security_score"] == 80

    @patch("requests.post")
    def test_get_pdf_report_success(self, mock_post):
        """Test getting PDF report."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake pdf"
        mock_response.headers = {"Content-Type": "application/pdf"}
        mock_post.return_value = mock_response

        config = _make_config_manager()
        manager = MobSFManager(config_manager=config)

        success, result = manager.get_pdf_report("abc123")

        assert success is True
        assert result == b"fake pdf"

    @patch("requests.post")
    def test_get_security_score_success(self, mock_post):
        """Test getting security score."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"score": 90}
        mock_post.return_value = mock_response

        config = _make_config_manager()
        manager = MobSFManager(config_manager=config)

        success, result = manager.get_security_score("abc123")

        assert success is True
        assert result["score"] == 90

    @patch("requests.get")
    def test_api_request_connection_error(self, mock_get):
        """Test API request handling connection error."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        config = _make_config_manager()
        manager = MobSFManager(config_manager=config)

        success, result = manager._make_api_request("about")

        assert success is False
        assert "Connection Error" in result

    def test_get_config(self):
        """Test get_config method."""
        config = _make_config_manager()
        manager = MobSFManager(config_manager=config)

        result = manager.config_manager

        assert result is config
