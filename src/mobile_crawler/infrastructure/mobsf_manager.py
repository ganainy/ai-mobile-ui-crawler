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
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

import requests

if TYPE_CHECKING:
    from mobile_crawler.config.config_manager import ConfigManager
    from mobile_crawler.infrastructure.adb_client import ADBClient
    from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager
    from mobile_crawler.infrastructure.run_repository import Run

logger = logging.getLogger(__name__)


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

        self.api_key = config_manager.get("mobsf_api_key") or ""
        self.api_url = config_manager.get("mobsf_api_url", "http://localhost:8000")
        if not self.api_url:
            raise ValueError("MOBSF_API_URL must be set in configuration")

        self.headers = {"Authorization": self.api_key}

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
    ) -> Tuple[bool, Any]:
        """Make an API request to MobSF.

        Args:
            endpoint: API endpoint (without the base URL)
            method: HTTP method (GET, POST)
            data: Form data for POST requests
            files: Files for multipart form submissions
            stream: Whether to stream the response

        Returns:
            Tuple of (success, response_data)
        """
        # Ensure endpoint doesn't start with a slash
        endpoint = endpoint.lstrip("/")

        # Ensure API URL has a scheme and is properly formatted
        api_url = self.api_url
        if not api_url.startswith(("http://", "https://")):
            api_url = f"http://{api_url}"
        api_url = api_url.rstrip("/") + "/"

        url = f"{api_url}api/v1/{endpoint}"
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, stream=stream, timeout=60)
            else:  # POST
                response = requests.post(
                    url, headers=self.headers, data=data, files=files, stream=stream, timeout=60
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
            error_msg = f"Timeout Error: Request to MobSF server timed out after 60 seconds"
            logger.error(f"Request timeout for {url}: {str(e)}")
            return False, error_msg
        except requests.RequestException as e:
            error_msg = f"Request Error: {str(e)}"
            logger.error(f"Request exception for {url}: {str(e)}")
            return False, error_msg
        except Exception as e:
            logger.error(f"Unexpected error during API request to {url}: {str(e)}")
            return False, f"Error: {str(e)}"

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

    def extract_apk_from_device(self, package_name: str) -> Optional[str]:
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
            # Get the path of the APK on the device
            path_cmd = ["shell", "pm", "path", package_name]
            result = subprocess.run(
                ["adb"] + path_cmd, capture_output=True, text=True, encoding="utf-8"
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

            base_apk_path = None
            for path in apk_paths:
                # The relevant path is the one containing "base.apk"
                if "base.apk" in path:
                    base_apk_path = path.strip()
                    break

            # If no base.apk is found, take the first path as a fallback
            if not base_apk_path and apk_paths:
                base_apk_path = apk_paths[0].strip()

            if not base_apk_path:
                logger.error("Could not find a valid APK path from 'pm path' output.")
                return None

            # Resolve output directory - use session directory if available
            output_dir = os.path.join("output_data", "extracted_apk")
            if self.session_folder_manager:
                # Will be resolved when we have a run object
                pass
            os.makedirs(output_dir, exist_ok=True)

            # Generate the local APK filename
            local_apk = os.path.join(output_dir, f"{package_name}.apk")

            # Pull the APK from the device
            pull_cmd = ["pull", base_apk_path, local_apk]
            pull_result = subprocess.run(
                ["adb"] + pull_cmd, capture_output=True, text=True, encoding="utf-8"
            )

            if pull_result.returncode != 0:
                logger.error(f"Failed to pull APK: {pull_result.stderr}")
                return None

            logger.info(f"APK extracted to: {local_apk}")
            return local_apk

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

    def get_report_json(self, file_hash: str) -> Tuple[bool, Dict[str, Any]]:
        """Get JSON report for a scanned file.

        Args:
            file_hash: The hash of the file

        Returns:
            Tuple of (success, report)
        """
        data = {"hash": file_hash}
        return self._make_api_request("report_json", "POST", data=data)

    def get_pdf_report(self, file_hash: str) -> Tuple[bool, bytes]:
        """Get PDF report for a scanned file.

        Args:
            file_hash: The hash of the file

        Returns:
            Tuple of (success, pdf_content)
        """
        data = {"hash": file_hash}
        return self._make_api_request("download_pdf", "POST", data=data)

    def save_pdf_report(
        self, file_hash: str, output_path: Optional[str] = None
    ) -> Optional[str]:
        """Save the PDF report to a file.

        Args:
            file_hash: The hash of the file
            output_path: Optional path to save the PDF, if not provided a default path is used

        Returns:
            Path to the saved PDF file, or None if saving failed
        """
        success, pdf_content = self.get_pdf_report(file_hash)
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
        self, file_hash: str, output_path: Optional[str] = None
    ) -> Optional[str]:
        """Save the JSON report to a file.

        Args:
            file_hash: The hash of the file
            output_path: Optional path to save the JSON, if not provided a default path is used

        Returns:
            Path to the saved JSON file, or None if saving failed
        """
        success, report = self.get_report_json(file_hash)
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

        # Log MobSF configuration
        _log(f"MobSF server: {self.api_url}", "blue")
        logger.debug(f"MobSF API URL: {self.api_url}")
        logger.debug(f"MobSF API key configured: {bool(self.api_key)}")

        # Resolve output directory
        if session_path:
            reports_dir = os.path.join(session_path, "reports")
        elif self.session_folder_manager and run_id:
            from mobile_crawler.infrastructure.run_repository import RunRepository
            from mobile_crawler.infrastructure.database import DatabaseManager

            db_manager = DatabaseManager()
            run_repo = RunRepository(db_manager)
            run = run_repo.get_run(run_id)
            if run and self.session_folder_manager:
                reports_dir = self.session_folder_manager.get_subfolder(run, "reports")
            else:
                reports_dir = os.path.join("output_data", "mobsf_reports")
        else:
            reports_dir = os.path.join("output_data", "mobsf_reports")

        os.makedirs(reports_dir, exist_ok=True)

        # Extract APK from device
        _log("Extracting APK from device...", "blue")
        logger.debug(f"Extracting APK for package: {package_name}")
        apk_path = self.extract_apk_from_device(package_name)
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

                    # Check if scan is complete based on log status
                    latest_log = log_entries[-1] if log_entries else {}
                    status = latest_log.get("status", "")
                    if "Completed" in status or "Error" in status or "Failed" in status:
                        _log(
                            f"Scan completed with status: {status}",
                            "green" if "Completed" in status else "red",
                        )
                        scan_complete = True
                        break

            # Also try to detect completion by checking if PDF report is available
            # This is more reliable than checking log status
            if attempt > 10:  # Wait at least 20 seconds before checking reports
                pdf_success, pdf_result = self.get_pdf_report(file_hash)
                if pdf_success and isinstance(pdf_result, bytes) and len(pdf_result) > 0:
                    _log("Scan completed - PDF report is available", "green")
                    scan_complete = True
                    break
                # Also check JSON report as fallback
                json_success, json_result = self.get_report_json(file_hash)
                if json_success and isinstance(json_result, dict) and json_result:
                    _log("Scan completed - JSON report is available", "green")
                    scan_complete = True
                    break

            if not scan_complete:
                if attempt == 0:
                    _log("Waiting for scan to start...", "blue")
                elif attempt % 15 == 0:  # Log progress every 30 seconds
                    elapsed = attempt * poll_interval
                    _log(f"Scan in progress... ({elapsed:.0f}s / {scan_timeout}s)", "blue")

            time.sleep(poll_interval)

        # Save reports only if scan is complete
        pdf_path = None
        json_path = None
        scorecard = None
        
        if scan_complete:
            _log("Generating reports...", "blue")
            pdf_path = os.path.join(reports_dir, f"{file_hash}_report.pdf")
            json_path = os.path.join(reports_dir, f"{file_hash}_report.json")

            pdf_path = self.save_pdf_report(file_hash, pdf_path)
            json_path = self.save_json_report(file_hash, json_path)

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
