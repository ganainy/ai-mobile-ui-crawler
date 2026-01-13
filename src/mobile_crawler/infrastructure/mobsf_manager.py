"""MobSF Manager for APK analysis.

Manages integration with Mobile Security Framework (MobSF) for
static analysis of Android applications.
"""

import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MobSFConfig:
    """Configuration for MobSF integration."""
    enabled: bool
    api_url: str = "http://localhost:8000"
    api_key: Optional[str] = None


@dataclass
class MobSFAnalysisResult:
    """Result of MobSF analysis."""
    success: bool
    report_path: Optional[str] = None
    json_path: Optional[str] = None
    error: Optional[str] = None
    scan_id: Optional[str] = None


class MobSFManager:
    """Manages MobSF integration for APK static analysis.

    Handles extracting APK from device, uploading to MobSF,
    retrieving analysis results (PDF + JSON), and managing
    the analysis workflow.
    """

    def __init__(self, adb_client=None, config: Optional[MobSFConfig] = None):
        """Initialize the MobSF manager.

        Args:
            adb_client: Optional ADB client wrapper for executing commands
            config: MobSFConfig with API settings
        """
        self._adb_client = adb_client
        self._config = config or MobSFConfig(enabled=False)
        self._session_folder_manager = None

    def set_session_folder_manager(self, manager):
        """Set the session folder manager for saving results.

        Args:
            manager: SessionFolderManager instance
        """
        self._session_folder_manager = manager

    def configure(self, config: MobSFConfig) -> None:
        """Configure MobSF settings.

        Args:
            config: MobSFConfig with API settings
        """
        self._config = config
        logger.info(f"MobSF configured: enabled={config.enabled}, url={config.api_url}")

    def analyze(self, package: str, device_id: str) -> MobSFAnalysisResult:
        """Analyze an APK using MobSF.

        Args:
            package: Android package name (e.g., com.example.app)
            device_id: Device ID for ADB operations

        Returns:
            MobSFAnalysisResult with report paths or error
        """
        if not self._config.enabled:
            logger.info("MobSF analysis disabled, skipping")
            return MobSFAnalysisResult(
                success=False,
                error="MobSF analysis is disabled in configuration"
            )

        if not self._config.api_key:
            logger.warning("MobSF API key not configured")
            return MobSFAnalysisResult(
                success=False,
                error="MobSF API key not configured"
            )

        try:
            # Extract APK from device
            apk_path = self._extract_apk(package, device_id)
            if not apk_path:
                return MobSFAnalysisResult(
                    success=False,
                    error=f"Failed to extract APK for package: {package}"
                )

            # Upload to MobSF
            scan_id = self._upload_to_mobsf(apk_path)
            if not scan_id:
                os.unlink(apk_path)
                return MobSFAnalysisResult(
                    success=False,
                    error="Failed to upload APK to MobSF"
                )

            # Generate and download reports
            pdf_path, json_path = self._download_reports(scan_id, package)

            # Clean up temporary APK
            try:
                os.unlink(apk_path)
            except Exception:
                pass

            if pdf_path or json_path:
                return MobSFAnalysisResult(
                    success=True,
                    report_path=pdf_path,
                    json_path=json_path,
                    scan_id=scan_id
                )
            else:
                return MobSFAnalysisResult(
                    success=False,
                    error="Failed to download reports from MobSF"
                )

        except Exception as e:
            logger.error(f"MobSF analysis failed: {e}")
            return MobSFAnalysisResult(
                success=False,
                error=str(e)
            )

    def analyze_run(self, run: 'Run', device_id: str) -> MobSFAnalysisResult:
        """Analyze an APK for a past run.
        
        Args:
            run: Run object for organizing results
            device_id: Device ID for ADB operations
            
        Returns:
            MobSFAnalysisResult with report paths or error
        """
        run_id = run.id
        package = run.app_package
        if not self._session_folder_manager:
            logger.warning("Session folder manager not configured")
            return MobSFAnalysisResult(
                success=False,
                error="Session folder manager not configured"
            )

        result = self.analyze(package, device_id)

        # Move reports to run's session folder if successful
        if result.success and self._session_folder_manager:
            reports_dir = self._session_folder_manager.get_subfolder(run, "reports")
            if reports_dir and os.path.exists(reports_dir):
                if result.report_path:
                    new_pdf_path = os.path.join(reports_dir, f"mobsf_report_{run_id}.pdf")
                    try:
                        os.rename(result.report_path, new_pdf_path)
                        result.report_path = new_pdf_path
                    except Exception as e:
                        logger.warning(f"Failed to move PDF report: {e}")

                if result.json_path:
                    new_json_path = os.path.join(reports_dir, f"mobsf_report_{run_id}.json")
                    try:
                        os.rename(result.json_path, new_json_path)
                        result.json_path = new_json_path
                    except Exception as e:
                        logger.warning(f"Failed to move JSON report: {e}")

        return result

    def _extract_apk(self, package: str, device_id: str) -> Optional[str]:
        """Extract APK from device.

        Args:
            package: Android package name
            device_id: Device ID for ADB operations

        Returns:
            Path to extracted APK, or None if failed
        """
        try:
            # Get APK path on device
            apk_path_cmd = f"-s {device_id} shell pm path {package}"
            apk_path_result = self._execute_adb_command(apk_path_cmd)

            if not apk_path_result or "package:" not in apk_path_result:
                logger.error(f"Package not found on device: {package}")
                return None

            # Extract package path from output
            device_apk_path = apk_path_result.split("package:")[1].strip()

            # Create temporary file for APK
            temp_dir = tempfile.gettempdir()
            local_apk_path = os.path.join(temp_dir, f"{package}.apk")

            # Pull APK from device
            pull_cmd = f"-s {device_id} pull {device_apk_path} {local_apk_path}"
            pull_result = self._execute_adb_command(pull_cmd)

            if pull_result is None:
                logger.error(f"Failed to pull APK from device")
                return None

            # Verify file exists
            if not os.path.exists(local_apk_path):
                logger.error(f"APK file not created at {local_apk_path}")
                return None

            logger.info(f"APK extracted to {local_apk_path}")
            return local_apk_path

        except Exception as e:
            logger.error(f"Error extracting APK: {e}")
            return None

    def _upload_to_mobsf(self, apk_path: str) -> Optional[str]:
        """Upload APK to MobSF for analysis.

        Args:
            apk_path: Path to local APK file

        Returns:
            Scan ID from MobSF, or None if failed
        """
        try:
            import requests

            url = f"{self._config.api_url}/api/v1/upload"
            headers = {
                "Authorization": self._config.api_key
            }

            with open(apk_path, "rb") as f:
                files = {"file": (os.path.basename(apk_path), f, "application/vnd.android.package-archive")}
                response = requests.post(url, headers=headers, files=files, timeout=60)

            if response.status_code != 200:
                logger.error(f"MobSF upload failed: {response.status_code} - {response.text}")
                return None

            result = response.json()
            scan_id = result.get("hash")

            if not scan_id:
                logger.error("MobSF upload response missing scan ID")
                return None

            logger.info(f"APK uploaded to MobSF, scan ID: {scan_id}")
            return scan_id

        except ImportError:
            logger.error("requests library not available for MobSF integration")
            return None
        except Exception as e:
            logger.error(f"Error uploading to MobSF: {e}")
            return None

    def _download_reports(self, scan_id: str, package: str) -> tuple[Optional[str], Optional[str]]:
        """Download PDF and JSON reports from MobSF.

        Args:
            scan_id: MobSF scan ID
            package: Package name for naming files

        Returns:
            Tuple of (pdf_path, json_path), either may be None
        """
        pdf_path = None
        json_path = None

        try:
            import requests

            # Download PDF report
            pdf_url = f"{self._config.api_url}/api/v1/download_pdf"
            pdf_headers = {"Authorization": self._config.api_key}
            pdf_data = {"hash": scan_id}

            pdf_response = requests.post(pdf_url, headers=pdf_headers, data=pdf_data, timeout=30)

            if pdf_response.status_code == 200:
                temp_dir = tempfile.gettempdir()
                pdf_path = os.path.join(temp_dir, f"{package}_mobsf_report.pdf")
                with open(pdf_path, "wb") as f:
                    f.write(pdf_response.content)
                logger.info(f"PDF report downloaded to {pdf_path}")
            else:
                logger.warning(f"Failed to download PDF report: {pdf_response.status_code}")

            # Download JSON report
            json_url = f"{self._config.api_url}/api/v1/report_json"
            json_response = requests.post(json_url, headers=pdf_headers, data=pdf_data, timeout=30)

            if json_response.status_code == 200:
                temp_dir = tempfile.gettempdir()
                json_path = os.path.join(temp_dir, f"{package}_mobsf_report.json")
                with open(json_path, "w") as f:
                    f.write(json_response.text)
                logger.info(f"JSON report downloaded to {json_path}")
            else:
                logger.warning(f"Failed to download JSON report: {json_response.status_code}")

            return pdf_path, json_path

        except ImportError:
            logger.error("requests library not available for MobSF integration")
            return None, None
        except Exception as e:
            logger.error(f"Error downloading reports from MobSF: {e}")
            return None, None

    def _execute_adb_command(self, command: str) -> Optional[str]:
        """Execute an ADB command.

        Args:
            command: ADB command to execute (without 'adb' prefix)

        Returns:
            Command output, or None if command failed
        """
        if self._adb_client:
            return self._adb_client.execute(command)

        # Fallback to subprocess if no ADB client provided
        import subprocess
        try:
            result = subprocess.run(
                ["adb"] + command.split(),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.error(f"ADB command timed out: {command}")
            return None
        except FileNotFoundError:
            logger.error("ADB not found in PATH")
            return None
        except Exception as e:
            logger.error(f"ADB command failed: {e}")
            return None

    def is_available(self) -> bool:
        """Check if MobSF is available.

        Returns:
            True if MobSF is reachable and configured
        """
        if not self._config.enabled:
            return False

        if not self._config.api_key:
            return False

        try:
            import requests
            url = f"{self._config.api_url}/api/v1/about"
            headers = {"Authorization": self._config.api_key}
            response = requests.get(url, headers=headers, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_config(self) -> MobSFConfig:
        """Get current MobSF configuration.

        Returns:
            Current MobSFConfig
        """
        return self._config
