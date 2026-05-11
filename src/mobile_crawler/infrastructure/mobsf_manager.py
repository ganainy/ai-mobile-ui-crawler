"""MobSF Manager for APK analysis.

Manages integration with Mobile Security Framework (MobSF) for
static analysis of Android applications.
"""

import base64
import json
import logging
import os
import re
import subprocess
import time
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

import requests

if TYPE_CHECKING:
    from mobile_crawler.config.config_manager import ConfigManager
    from mobile_crawler.infrastructure.adb_client import ADBClient
    from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager
    from mobile_crawler.infrastructure.run_repository import Run

logger = logging.getLogger(__name__)

MOBSF_CONTAINER_NAME = "mobile-crawler-mobsf"
MOBSF_API_KEY_FILE = ".mobsf_api_key"
MOBSF_KEY_DISCOVERY_ERROR = (
    "MobSF API key could not be discovered from .mobsf_api_key or Docker logs for "
    "mobile-crawler-mobsf. Start MobSF with scripts/start.ps1."
)
MOBSF_INVALID_KEY_ERROR = "MobSF API key is invalid; refreshed Docker key did not authenticate."


class MobSFAnalysisResult:
    """Result of MobSF analysis."""

    def __init__(
        self,
        success: bool,
        report_path: Optional[str] = None,
        json_path: Optional[str] = None,
        error: Optional[str] = None,
        scan_id: Optional[str] = None,
        security_score: Optional[Dict[str, Any]] = None,
    ):
        """Initialize analysis result.

        Args:
            success: Whether analysis completed successfully
            report_path: Path to PDF report
            json_path: Path to JSON report
            error: Error message if failed
            scan_id: MobSF scan ID
            security_score: Security scorecard data
        """
        self.success = success
        self.report_path = report_path
        self.json_path = json_path
        self.error = error
        self.scan_id = scan_id
        self.security_score = security_score


class MobSFManager:
    """Manages MobSF integration for APK static analysis.

    Handles extracting APK from device, uploading to MobSF,
    retrieving analysis results (PDF + JSON), and managing
    the analysis workflow with progress monitoring.
    """

    def __init__(
        self,
        config_manager: "ConfigManager",
        adb_client: Optional["ADBClient"] = None,
        session_folder_manager: Optional["SessionFolderManager"] = None,
    ):
        """Initialize the MobSF manager.

        Args:
            config_manager: Configuration manager instance
            adb_client: Optional ADB client wrapper for executing commands
            session_folder_manager: Optional session folder manager for path resolution
        """
        self.config_manager = config_manager
        self.adb_client = adb_client
        self.session_folder_manager = session_folder_manager

        self.api_key = ""
        self.api_url = config_manager.get("mobsf_api_url", "http://localhost:8000")
        if not self.api_url:
            raise ValueError("MOBSF_API_URL must be set in configuration")

        self.headers = {"Authorization": ""}

    @property
    def scan_results_dir(self) -> str:
        """Lazily resolve the scan results directory path.

        Returns:
            Path to scan results directory
        """
        # Default to reports subdirectory in session folder
        # This will be resolved when perform_complete_scan is called with a run
        return os.path.join("output_data", "mobsf_reports")

    def _make_api_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        timeout: Optional[int] = None,
    ) -> Tuple[bool, Any]:
        """Make an API request to MobSF.

        Args:
            endpoint: API endpoint (without the base URL)
            method: HTTP method (GET, POST)
            data: Form data for POST requests
            files: Files for multipart form submissions
            stream: Whether to stream the response
            timeout: Request timeout in seconds

        Returns:
            Tuple of (success, response_data)
        """
        api_url, api_key = self._refresh_runtime_config()
        if not api_key:
            return False, MOBSF_KEY_DISCOVERY_ERROR

        # Ensure endpoint doesn't start with a slash
        endpoint = endpoint.lstrip("/")

        url = self._build_api_url(api_url, endpoint)

        # Get timeout from config if not specified
        if timeout is None:
            timeout = int(self.config_manager.get("mobsf_request_timeout", 300))

        headers = {"Authorization": api_key, "X-Mobsf-Api-Key": api_key}
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, stream=stream, timeout=timeout)
            else:  # POST
                response = requests.post(
                    url, headers=headers, data=data, files=files, stream=stream, timeout=timeout
                )

            if response.status_code == 200:
                if stream:
                    return True, response
                if response.headers.get("Content-Type") == "application/pdf":
                    return True, response.content
                try:
                    return True, response.json()
                except ValueError:
                    return True, response.text
            else:
                error_msg = f"API Error: {response.status_code} - {response.text[:200]}"
                logger.error(
                    f"API request failed: {url}, Status: {response.status_code}, "
                    f"Response: {response.text[:200]}"
                )
                return False, error_msg
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection Error: Cannot connect to MobSF server at {url}. Is the server running?"
            logger.error(f"Request exception for {url}: {str(e)}")
            return False, error_msg
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout Error: Request to MobSF server timed out after {timeout} seconds"
            logger.error(f"Request timeout for {url}: {str(e)}")
            return False, error_msg
        except requests.RequestException as e:
            error_msg = f"Request Error: {str(e)}"
            logger.error(f"Request exception for {url}: {str(e)}")
            return False, error_msg
        except Exception as e:
            logger.error(f"Unexpected error during API request to {url}: {str(e)}")
            return False, f"Error: {str(e)}"

    def _refresh_runtime_config(self) -> Tuple[str, str]:
        """Read MobSF URL and resolve the API key from automatic sources."""
        api_url = self.config_manager.get("mobsf_api_url", "http://localhost:8000")
        if not api_url:
            raise ValueError("MOBSF_API_URL must be set in configuration")

        api_key = self._resolve_api_key()

        self.api_url = api_url
        self.api_key = api_key
        self.headers = {"Authorization": api_key, "X-Mobsf-Api-Key": api_key}
        return api_url, api_key

    def _build_api_url(self, api_url: str, endpoint: str) -> str:
        """Build a MobSF API URL for an endpoint."""
        if not api_url.startswith(("http://", "https://")):
            api_url = f"http://{api_url}"
        api_url = api_url.rstrip("/")
        endpoint = endpoint.lstrip("/")
        if api_url.endswith("/api/v1"):
            return f"{api_url}/{endpoint}"
        return f"{api_url}/api/v1/{endpoint}"

    def _resolve_api_key(self, force_docker_refresh: bool = False) -> str:
        """Resolve the MobSF API key from file, Docker logs, then legacy sources."""
        if not force_docker_refresh:
            key_file = self._find_api_key_file()
            if key_file and key_file.exists():
                try:
                    api_key = key_file.read_text(encoding="utf-8").strip()
                    if api_key:
                        return api_key
                except OSError as e:
                    logger.warning("Failed to read MobSF API key file %s: %s", key_file, e)

        docker_key = self._discover_api_key_from_docker_logs()
        if docker_key:
            self._save_api_key_file(docker_key)
            return docker_key

        if not force_docker_refresh:
            legacy_key = (
                os.environ.get("CRAWLER_MOBSF_API_KEY")
                or self.config_manager.get("mobsf_api_key")
                or ""
            ).strip()
            if legacy_key:
                return legacy_key

        return ""

    def _find_api_key_file(self) -> Optional[Path]:
        """Find .mobsf_api_key in the current working tree or parents."""
        for parent in [Path.cwd(), *Path.cwd().parents]:
            candidate = parent / MOBSF_API_KEY_FILE
            if candidate.exists():
                return candidate
        return None

    def _api_key_write_path(self) -> Path:
        """Return the path used to cache a discovered MobSF API key."""
        existing = self._find_api_key_file()
        return existing if existing else Path.cwd() / MOBSF_API_KEY_FILE

    def _save_api_key_file(self, api_key: str) -> None:
        """Cache a discovered MobSF API key for future runs."""
        try:
            self._api_key_write_path().write_text(f"{api_key}\n", encoding="utf-8")
        except OSError as e:
            logger.warning("Failed to save MobSF API key file: %s", e)

    def _discover_api_key_from_docker_logs(self) -> str:
        """Extract the MobSF REST API key from the managed Docker container logs."""
        try:
            result = subprocess.run(
                ["docker", "logs", MOBSF_CONTAINER_NAME],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError) as e:
            logger.warning("Failed to read MobSF Docker logs: %s", e)
            return ""

        logs = f"{result.stdout}\n{result.stderr}"
        logs = re.sub(r"\x1b\[[0-9;]*m", "", logs)
        match = re.search(r"REST API Key:\s*([A-Fa-f0-9]+)", logs)
        if match:
            return match.group(1).strip()
        return ""

    def _validate_api_key(self, api_url: str, api_key: str) -> Tuple[bool, Optional[str]]:
        """Validate a MobSF API key against an authenticated API endpoint."""
        url = self._build_api_url(api_url, "scans")
        timeout = int(self.config_manager.get("mobsf_request_timeout", 300))
        headers = {"Authorization": api_key, "X-Mobsf-Api-Key": api_key}
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
        except requests.exceptions.ConnectionError:
            return False, f"Connection Error: Cannot connect to MobSF server at {url}. Is the server running?"
        except requests.exceptions.Timeout:
            return False, f"Timeout Error: Request to MobSF server timed out after {timeout} seconds"
        except requests.RequestException as e:
            return False, f"Request Error: {e}"

        if response.status_code == 200:
            return True, None
        if response.status_code == 401:
            return False, "401"
        return False, f"API Error: {response.status_code} - {response.text[:200]}"

    def preflight(self) -> Tuple[bool, str]:
        """Resolve and validate MobSF authentication before expensive APK work."""
        api_url, api_key = self._refresh_runtime_config()
        if not api_key:
            return False, MOBSF_KEY_DISCOVERY_ERROR

        valid, error = self._validate_api_key(api_url, api_key)
        if valid:
            return True, ""

        if error == "401":
            refreshed_key = self._resolve_api_key(force_docker_refresh=True)
            if refreshed_key and refreshed_key != api_key:
                self.api_key = refreshed_key
                self.headers = {"Authorization": refreshed_key, "X-Mobsf-Api-Key": refreshed_key}
                refreshed_valid, refreshed_error = self._validate_api_key(api_url, refreshed_key)
                if refreshed_valid:
                    return True, ""
                if refreshed_error == "401":
                    return False, MOBSF_INVALID_KEY_ERROR
                return False, refreshed_error or MOBSF_INVALID_KEY_ERROR
            return False, MOBSF_INVALID_KEY_ERROR

        return False, error or MOBSF_KEY_DISCOVERY_ERROR

    def _adb_base_command(self, device_id: Optional[str] = None) -> List[str]:
        """Build the configured ADB command prefix."""
        adb_executable = self.config_manager.get("adb_executable_path", "adb") or "adb"
        command = [adb_executable]
        if device_id:
            command.extend(["-s", device_id])
        return command

    async def _run_adb_command_async(
        self, command_list: List[str], suppress_stderr: bool = False
    ) -> Tuple[str, int]:
        """Async helper to run ADB commands.

        Args:
            command_list: List of ADB command arguments (without 'adb' prefix)
            suppress_stderr: If True, don't log stderr output

        Returns:
            Tuple of (combined_output, return_code)
        """
        if self.adb_client:
            return await self.adb_client.execute_async(command_list, suppress_stderr)

        # Fallback: create temporary ADB client
        from mobile_crawler.infrastructure.adb_client import ADBClient

        adb_executable = self.config_manager.get("adb_executable_path", "adb")
        temp_client = ADBClient(adb_executable=adb_executable)
        return await temp_client.execute_async(command_list, suppress_stderr)

    def extract_apk_from_device(
        self, package_name: str, output_dir: Optional[str] = None, device_id: Optional[str] = None
    ) -> Optional[str]:
        """Extract the APK file from a connected Android device using ADB.

        Args:
            package_name: The package name of the app to extract

        Returns:
            Path to the extracted APK file, or None if extraction failed
        """
        if not self.config_manager.get("enable_mobsf_analysis", False):
            logger.warning("MobSF analysis is disabled, skipping APK extraction")
            return None

        try:
            adb_prefix = self._adb_base_command(device_id)
            path_cmd = ["shell", "pm", "path", package_name]
            result = subprocess.run(
                adb_prefix + path_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode != 0 or not result.stdout.strip():
                logger.error(f"Failed to get APK path: {result.stderr}")
                return None

            # The output can contain multiple paths for split APKs.
            # The format is "package:/path/to/apk". We use regex to handle potential variations.
            raw_output = result.stdout.strip()
            apk_paths = re.findall(r"package:(.*)", raw_output)

            if not apk_paths:
                logger.error(f"Failed to parse APK path from output: {raw_output}")
                return None

            apk_paths = [path.strip() for path in apk_paths if path.strip()]

            # Resolve output directory - use provided directory or session directory if available
            if output_dir:
                selected_output_dir = output_dir
            else:
                selected_output_dir = os.path.join("output_data", "apks")
            
            os.makedirs(selected_output_dir, exist_ok=True)

            pulled_files = []
            for index, remote_apk in enumerate(apk_paths):
                remote_name = os.path.basename(remote_apk) or f"split_{index}.apk"
                safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", remote_name)
                if len(apk_paths) == 1:
                    local_apk = os.path.join(selected_output_dir, f"{package_name}.apk")
                else:
                    local_apk = os.path.join(selected_output_dir, f"{index:02d}_{safe_name}")

                pull_cmd = ["pull", remote_apk, local_apk]
                pull_result = subprocess.run(
                    adb_prefix + pull_cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

                if pull_result.returncode != 0:
                    logger.error(f"Failed to pull APK {remote_apk}: {pull_result.stderr}")
                    return None
                pulled_files.append(local_apk)

            if len(pulled_files) == 1:
                logger.info(f"APK extracted to: {pulled_files[0]}")
                return pulled_files[0]

            archive_path = os.path.join(selected_output_dir, f"{package_name}.apks")
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for pulled_file in pulled_files:
                    archive.write(pulled_file, arcname=os.path.basename(pulled_file))

            logger.info(f"Split APK archive extracted to: {archive_path}")
            return archive_path

        except Exception as e:
            logger.error(f"Error extracting APK: {str(e)}")
            return None

    def upload_apk(self, apk_path: str) -> Tuple[bool, Dict[str, Any]]:
        """Upload an APK file to MobSF for analysis.

        Args:
            apk_path: Path to the APK file

        Returns:
            Tuple of (success, response_data)
        """
        if not os.path.exists(apk_path):
            logger.error(f"APK file not found: {apk_path}")
            return False, {"error": "APK file not found"}

        try:
            with open(apk_path, "rb") as apk_file:
                files = {
                    "file": (os.path.basename(apk_path), apk_file, "application/octet-stream")
                }
                return self._make_api_request("upload", "POST", files=files)
        except Exception as e:
            logger.error(f"Error uploading APK: {str(e)}")
            return False, {"error": str(e)}

    def scan_apk(self, file_hash: str, rescan: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """Scan an uploaded APK file.

        Args:
            file_hash: The hash of the uploaded file
            rescan: Whether to rescan an already analyzed file

        Returns:
            Tuple of (success, scan_results)
        """
        data = {"hash": file_hash, "re_scan": 1 if rescan else 0}
        return self._make_api_request("scan", "POST", data=data)

    def get_scan_logs(self, file_hash: str) -> Tuple[bool, Dict[str, Any]]:
        """Get scan logs for a file.

        Args:
            file_hash: The hash of the file

        Returns:
            Tuple of (success, logs)
        """
        data = {"hash": file_hash}
        return self._make_api_request("scan_logs", "POST", data=data)

    def get_report_json(self, file_hash: str, timeout: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """Get JSON report for a scanned file.

        Args:
            file_hash: The hash of the file
            timeout: Request timeout in seconds

        Returns:
            Tuple of (success, report)
        """
        data = {"hash": file_hash}
        return self._make_api_request("report_json", "POST", data=data, timeout=timeout)

    def get_pdf_report(self, file_hash: str, timeout: Optional[int] = None) -> Tuple[bool, bytes]:
        """Get PDF report for a scanned file.

        Args:
            file_hash: The hash of the file
            timeout: Request timeout in seconds

        Returns:
            Tuple of (success, pdf_content)
        """
        data = {"hash": file_hash}
        return self._make_api_request("download_pdf", "POST", data=data, timeout=timeout)

    def save_pdf_report(
        self, file_hash: str, output_path: Optional[str] = None, timeout: Optional[int] = None
    ) -> Optional[str]:
        """Save the PDF report to a file.

        Args:
            file_hash: The hash of the file
            output_path: Optional path to save the PDF, if not provided a default path is used
            timeout: Request timeout in seconds

        Returns:
            Path to the saved PDF file, or None if saving failed
        """
        success, pdf_content = self.get_pdf_report(file_hash, timeout=timeout)
        if not success:
            logger.error(f"Failed to get PDF report: {pdf_content}")
            return None

        if output_path is None:
            output_path = os.path.join(self.scan_results_dir, f"{file_hash}_report.pdf")

        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as pdf_file:
                pdf_file.write(pdf_content)
            logger.info(f"PDF report saved: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error saving PDF report: {str(e)}")
            return None

    def save_json_report(
        self, file_hash: str, output_path: Optional[str] = None, timeout: Optional[int] = None
    ) -> Optional[str]:
        """Save the JSON report to a file.

        Args:
            file_hash: The hash of the file
            output_path: Optional path to save the JSON, if not provided a default path is used
            timeout: Request timeout in seconds

        Returns:
            Path to the saved JSON file, or None if saving failed
        """
        success, report = self.get_report_json(file_hash, timeout=timeout)
        if not success:
            logger.error(f"Failed to get JSON report: {report}")
            return None

        if output_path is None:
            output_path = os.path.join(self.scan_results_dir, f"{file_hash}_report.json")

        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as json_file:
                json.dump(report, json_file, indent=4)
            logger.info(f"JSON report saved: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error saving JSON report: {str(e)}")
            return None

    def get_security_score(self, file_hash: str) -> Tuple[bool, Dict[str, Any]]:
        """Get security scorecard for a scanned file.

        Args:
            file_hash: The hash of the file

        Returns:
            Tuple of (success, scorecard)
        """
        data = {"hash": file_hash}
        return self._make_api_request("scorecard", "POST", data=data)

    def perform_complete_scan(
        self,
        package_name: str,
        run_id: Optional[int] = None,
        session_path: Optional[str] = None,
        device_id: Optional[str] = None,
        log_callback: Optional[Callable[[str, Optional[str]], None]] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Perform a complete scan workflow.

        1. Extract APK from device
        2. Upload to MobSF
        3. Scan the APK
        4. Get and save reports

        Args:
            package_name: The package name to scan
            run_id: Optional run ID for organizing results
            session_path: Optional session directory path
            log_callback: Optional callback function to display logs.
                         Should accept (message: str, color: Optional[str] = None)

        Returns:
            Tuple of (success, scan_summary)
        """
        def _log(message: str, color: Optional[str] = None):
            """Helper to log messages via callback or standard logging."""
            if log_callback:
                log_callback(message, color)
            else:
                logger.info(message)

        # Double-check that MobSF is enabled before proceeding
        if not self.config_manager.get("enable_mobsf_analysis", False):
            logger.warning("MobSF analysis is disabled, skipping APK extraction and scan")
            _log("MobSF analysis is disabled, skipping", "orange")
            return False, {"error": "MobSF analysis is disabled"}

        try:
            preflight_ok, preflight_error = self.preflight()
        except ValueError as e:
            _log(f"ERROR: {e}", "red")
            return False, {"error": str(e)}

        if not preflight_ok:
            logger.error(preflight_error)
            _log(f"ERROR: {preflight_error}", "red")
            return False, {"error": preflight_error}

        # Log MobSF configuration
        _log(f"MobSF server: {self.api_url}", "blue")
        logger.debug(f"MobSF API URL: {self.api_url}")
        logger.debug(f"MobSF API key configured: {bool(self.api_key)}")

        # Resolve output directory
        if session_path:
            reports_dir = os.path.join(session_path, "reports")
            apks_dir = os.path.join(session_path, "apks")
        elif self.session_folder_manager and run_id:
            from mobile_crawler.infrastructure.run_repository import RunRepository
            from mobile_crawler.infrastructure.database import DatabaseManager

            db_manager = DatabaseManager()
            run_repo = RunRepository(db_manager)
            run = run_repo.get_run_by_id(run_id)
            if run and self.session_folder_manager:
                reports_dir = self.session_folder_manager.get_subfolder(run, "reports")
                apks_dir = self.session_folder_manager.get_subfolder(run, "apks")
            else:
                reports_dir = os.path.join("output_data", "mobsf_reports")
                apks_dir = os.path.join("output_data", "apks")
        else:
            reports_dir = os.path.join("output_data", "mobsf_reports")
            apks_dir = os.path.join("output_data", "apks")

        os.makedirs(reports_dir, exist_ok=True)
        os.makedirs(apks_dir, exist_ok=True)

        # Extract APK from device
        _log("Extracting APK from device...", "blue")
        logger.debug(f"Extracting APK for package: {package_name}")
        apk_path = self.extract_apk_from_device(package_name, output_dir=apks_dir, device_id=device_id)
        if not apk_path:
            error_msg = "Failed to extract APK from device"
            logger.error(f"MobSF analysis failed: {error_msg}")
            _log(f"ERROR: {error_msg}", "red")
            return False, {"error": error_msg}
        _log(f"APK extracted to: {apk_path}", "green")
        logger.debug(f"APK extracted successfully: {apk_path}")

        # Upload APK to MobSF
        _log("Uploading APK to MobSF...", "blue")
        logger.debug(f"Uploading APK to MobSF server: {self.api_url}")
        upload_success, upload_result = self.upload_apk(apk_path)
        if not upload_success:
            error_msg = f"Failed to upload APK: {upload_result}"
            logger.error(f"MobSF analysis failed: {error_msg}")
            _log(f"ERROR: {error_msg}", "red")
            # Check if it's a connection error
            if "Connection" in str(upload_result) or "refused" in str(upload_result).lower():
                _log("MobSF server appears to be unreachable. Is the server running?", "red")
                logger.error("MobSF server unreachable - check if server is running")
            return False, {"error": error_msg}

        file_hash = upload_result.get("hash")
        if not file_hash:
            return False, {"error": "No file hash in upload response"}
        _log(f"APK uploaded successfully. Hash: {file_hash}", "green")

        # Scan the APK
        _log("Starting MobSF static analysis...", "blue")
        logger.debug(f"Initiating MobSF scan for hash: {file_hash}")
        scan_success, scan_result = self.scan_apk(file_hash)
        if not scan_success:
            error_msg = f"Failed to scan APK: {scan_result}"
            logger.error(f"MobSF analysis failed: {error_msg}")
            _log(f"ERROR: {error_msg}", "red")
            return False, {"error": error_msg}
        logger.debug("MobSF scan initiated successfully")
        _log("MobSF scan started successfully", "green")

        # Wait for scan to complete and display logs
        scan_timeout = int(self.config_manager.get("mobsf_scan_timeout", 900))
        poll_interval = float(self.config_manager.get("mobsf_poll_interval", 2))
        max_retries = int(scan_timeout / poll_interval)
        last_log_count = 0
        seen_logs = set()
        scan_complete = False

        _log(f"Waiting for scan to complete (timeout: {scan_timeout}s, polling every {poll_interval}s)...", "blue")

        for attempt in range(max_retries):
            # Try to get scan logs for progress updates
            logs_success, logs = self.get_scan_logs(file_hash)
            if logs_success and "logs" in logs:
                log_entries = logs.get("logs", [])

                # Display new log entries
                if log_entries:
                    for log_entry in log_entries[last_log_count:]:
                        log_id = (
                            f"{log_entry.get('timestamp', '')}-"
                            f"{log_entry.get('status', '')}-{log_entry.get('message', '')}"
                        )
                        if log_id not in seen_logs:
                            seen_logs.add(log_id)
                            status = log_entry.get("status", "")
                            message = log_entry.get("message", "")
                            timestamp = log_entry.get("timestamp", "")

                            if message:
                                log_message = f"[MobSF] {message}"
                                if timestamp:
                                    log_message = f"[{timestamp}] {log_message}"

                                # Determine color based on status
                                if "Error" in status or "Failed" in status:
                                    color = "red"
                                elif "Completed" in status or "Success" in status:
                                    color = "green"
                                elif "Warning" in status:
                                    color = "orange"
                                else:
                                    color = "blue"

                                _log(log_message, color)

                            if status and status not in message:
                                _log(f"[MobSF] Status: {status}", "blue")

                    last_log_count = len(log_entries)

            # Treat report availability as the completion signal across MobSF versions.
            json_success, json_result = self.get_report_json(file_hash, timeout=10)
            if json_success and isinstance(json_result, dict) and json_result:
                _log("Scan completed - JSON report is available", "green")
                scan_complete = True
                break
            pdf_success, pdf_result = self.get_pdf_report(file_hash, timeout=10)
            if pdf_success and isinstance(pdf_result, bytes) and len(pdf_result) > 0:
                _log("Scan completed - PDF report is available", "green")
                scan_complete = True
                break

            if not scan_complete:
                if attempt == 0:
                    _log("Waiting for scan to start...", "blue")
                elif attempt % 15 == 0:  # Log progress every 30 seconds
                    elapsed = attempt * poll_interval
                    _log(f"Scan in progress... ({elapsed:.0f}s / {scan_timeout}s)", "blue")
                    logger.info(f"MobSF scan for {file_hash} still in progress: {elapsed:.0f}s elapsed")

            time.sleep(poll_interval)

        # Save reports only if scan is complete
        pdf_path = None
        json_path = None
        scorecard = None
        
        if scan_complete:
            _log("Generating reports...", "blue")
            pdf_path = os.path.join(reports_dir, f"{file_hash}_report.pdf")
            json_path = os.path.join(reports_dir, f"{file_hash}_report.json")

            req_timeout = int(self.config_manager.get("mobsf_request_timeout", 300))
            pdf_path = self.save_pdf_report(file_hash, pdf_path, timeout=req_timeout)
            json_path = self.save_json_report(file_hash, json_path, timeout=req_timeout)

            if pdf_path:
                _log(f"PDF report saved: {pdf_path}", "green")
            if json_path:
                _log(f"JSON report saved: {json_path}", "green")

            # Get security score
            _log("Retrieving security score...", "blue")
            score_success, scorecard = self.get_security_score(file_hash)
            if score_success and isinstance(scorecard, dict):
                score_value = scorecard.get("score", "N/A")
                _log(f"Security Score: {score_value}", "green")
        else:
            _log(f"Warning: Scan timeout reached ({scan_timeout}s). Reports may not be available yet.", "orange")
            _log("You can manually retrieve reports later using the file hash.", "orange")
            _log(f"File hash: {file_hash}", "blue")

        # Prepare summary
        summary = {
            "package_name": package_name,
            "file_hash": file_hash,
            "apk_path": apk_path,
            "pdf_report": pdf_path,
            "json_report": json_path,
            "security_score": scorecard if scorecard else "Unknown",
            "scan_complete": scan_complete,
        }

        if scan_complete:
            _log("MobSF analysis completed successfully!", "green")
            return True, summary
        else:
            _log("MobSF analysis timed out - scan may still be in progress", "orange")
            return False, summary

    def analyze_run(
        self, run: "Run", device_id: str
    ) -> MobSFAnalysisResult:
        """Analyze an APK for a past run (compatibility method for UI).

        This method provides compatibility with the old interface used by RunHistoryView.
        It wraps perform_complete_scan and returns a MobSFAnalysisResult.

        Args:
            run: Run object for organizing results
            device_id: Device ID for ADB operations

        Returns:
            MobSFAnalysisResult with report paths or error
        """
        if not self.config_manager.get("enable_mobsf_analysis", False):
            return MobSFAnalysisResult(
                success=False,
                error="MobSF analysis is disabled in configuration"
            )

        # Get session path from run
        session_path = None
        if hasattr(run, "session_path") and run.session_path:
            session_path = run.session_path
        elif self.session_folder_manager:
            session_path = self.session_folder_manager.get_session_path(run)

        # Perform complete scan
        success, summary = self.perform_complete_scan(
            package_name=run.app_package,
            run_id=run.id,
            session_path=session_path,
            device_id=device_id,
            log_callback=None,  # UI will handle logging separately
        )

        if success:
            return MobSFAnalysisResult(
                success=True,
                report_path=summary.get("pdf_report"),
                json_path=summary.get("json_report"),
                scan_id=summary.get("file_hash"),
                security_score=summary.get("security_score"),
            )
        else:
            return MobSFAnalysisResult(
                success=False,
                error=summary.get("error", "Unknown error"),
            )
