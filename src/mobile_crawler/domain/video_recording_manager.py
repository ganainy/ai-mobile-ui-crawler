"""Video recording manager for screen recording during crawls."""

import base64
import logging
import os
import time
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from mobile_crawler.config.config_manager import ConfigManager
    from mobile_crawler.infrastructure.appium_driver import AppiumDriver
    from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager

logger = logging.getLogger(__name__)


class VideoRecordingManager:
    """Manages screen recording using Appium's built-in recording capabilities.

    Handles starting/stopping video recording during crawl sessions,
    saving videos to session directories with proper naming.
    """

    def __init__(
        self,
        appium_driver: "AppiumDriver",
        config_manager: "ConfigManager",
        session_folder_manager: Optional["SessionFolderManager"] = None,
    ):
        """Initialize video recording manager.

        Args:
            appium_driver: Appium driver instance
            config_manager: Configuration manager instance
            session_folder_manager: Optional session folder manager for path resolution
        """
        self.appium_driver = appium_driver
        self.config_manager = config_manager
        self.session_folder_manager = session_folder_manager

        self.video_recording_enabled: bool = bool(
            config_manager.get("enable_video_recording", False)
        )
        logger.debug(f"VideoRecordingManager initialized, enabled: {self.video_recording_enabled}")

        self.video_file_path: Optional[str] = None
        self._is_recording: bool = False

    def is_recording(self) -> bool:
        """Returns whether recording is currently active.

        Returns:
            True if recording is active, False otherwise
        """
        return self._is_recording

    def start_recording(
        self,
        run_id: Optional[int] = None,
        step_num: Optional[int] = None,
        session_path: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Starts video recording.

        Args:
            run_id: Optional run ID for filename generation
            step_num: Optional step number for filename generation
            session_path: Optional session directory path for output

        Returns:
            Tuple containing (success, reason_message)
        """
        logger.info(f"start_recording called: video_recording_enabled={self.video_recording_enabled}, run_id={run_id}, session_path={session_path}")
        logger.debug(f"[DEBUG] VideoRecordingManager.start_recording - enabled={self.video_recording_enabled}, run_id={run_id}, step_num={step_num}, session_path={session_path}")
        
        if not self.video_recording_enabled:
            return False, "Video recording disabled in config"

        if self._is_recording:
            return True, "Already recording"

        try:
            # Check if AppiumDriver is available
            if not self.appium_driver:
                return False, "AppiumDriver instance not available"
            
            # Verify driver is connected
            try:
                self.appium_driver.get_driver()
            except Exception:
                return False, "Appium WebDriver not connected"
            
            # Generate filename
            target_app_package = str(self.config_manager.get("app_package", ""))
            if not target_app_package:
                return False, "Application package not configured"
            
            sanitized_package = target_app_package.replace(".", "_")
            timestamp = time.strftime("%Y%m%d_%H%M%S")

            if run_id is not None and step_num is not None:
                video_filename = (
                    f"{sanitized_package}_run{run_id}_step{step_num}_{timestamp}.mp4"
                )
            else:
                video_filename = f"{sanitized_package}_{timestamp}.mp4"

            # Resolve output directory
            if session_path:
                video_output_dir = os.path.join(session_path, "videos")
            elif self.session_folder_manager and run_id:
                # Assuming generic output path if repo lookup is too complex here.
                video_output_dir = os.path.join("output_data", "videos")
            else:
                video_output_dir = os.path.join("output_data", "videos")

            # Better directory resolution logic from original code
            if not session_path and self.session_folder_manager and run_id:
                 try:
                    from mobile_crawler.infrastructure.database import DatabaseManager
                    from mobile_crawler.infrastructure.run_repository import RunRepository
                    # This is heavy but was in original code
                    db_manager = DatabaseManager()
                    run_repo = RunRepository(db_manager)
                    run = run_repo.get_run_by_id(run_id)
                    if run:
                        video_output_dir = self.session_folder_manager.get_subfolder(run, "videos")
                 except Exception:
                     pass

            try:
                os.makedirs(video_output_dir, exist_ok=True)
            except OSError as e:
                return False, f"Failed to create video directory: {e}"

            # Set the full path
            self.video_file_path = os.path.join(video_output_dir, video_filename)

            # Start recording
            try:
                self.appium_driver.start_recording_screen()
                self._is_recording = True
                return True, "Recording started successfully"
            except Exception as e:
                self.video_file_path = None
                self._is_recording = False
                logger.error(f"Appium start_recording_screen failed: {e}", exc_info=True)
                return False, f"Appium error: {str(e)}"

        except Exception as e:
            logger.error(f"Error starting video recording: {e}", exc_info=True)
            self.video_file_path = None
            self._is_recording = False
            return False, f"Unexpected error: {str(e)}"

    def stop_recording_and_save(self) -> Tuple[Optional[str], str]:
        """Stops video recording and saves the file.

        Returns:
            Tuple containing (path to saved video file or None, reason message)
        """
        if not self.video_recording_enabled:
            return None, "Video recording disabled"

        if not self._is_recording:
            return None, "Recording was not started"

        try:
            # Stop recording and get video data (base64 string)
            try:
                video_base64 = self.appium_driver.stop_recording_screen()
            except Exception as e:
                self._is_recording = False
                return None, f"Failed to stop recording: {str(e)}"
                
            self._is_recording = False
            
            if not video_base64:
                self.video_file_path = None
                return None, "No video data received from driver"

            if not self.video_file_path:
                return None, "Video file path not set"

            # Decode base64 and save to file
            try:
                video_bytes = base64.b64decode(video_base64)
            except Exception as e:
                self.video_file_path = None
                return None, f"Failed to decode video data: {str(e)}"

            # Ensure directory exists
            try:
                os.makedirs(os.path.dirname(self.video_file_path), exist_ok=True)
            except OSError as e:
                return None, f"Failed to create directory: {str(e)}"

            # Save video to file
            try:
                with open(self.video_file_path, "wb") as f:
                    f.write(video_bytes)
            except OSError as e:
                return None, f"Failed to write video file: {str(e)}"

            if os.path.exists(self.video_file_path):
                file_size = os.path.getsize(self.video_file_path)
                if file_size > 0:
                    saved_path = os.path.abspath(self.video_file_path)
                    logger.info(f"Video recording saved: {saved_path} ({file_size} bytes)")
                    self.video_file_path = None  # Reset after successful save
                    return saved_path, "Success"
                else:
                    return os.path.abspath(self.video_file_path), "File saved but empty"
            else:
                self.video_file_path = None
                return None, "File save verification failed"

        except Exception as e:
            logger.error(f"Error stopping/saving video recording: {e}", exc_info=True)
            self._is_recording = False
            self.video_file_path = None
            return None, f"Unexpected error: {str(e)}"

    def save_partial_on_crash(self) -> Optional[str]:
        """Attempt to save partial recording on crash.

        This method can be called in exception handlers to save
        any available recording data.

        Returns:
            Path to saved partial video file, or None if failed
        """
        if not self._is_recording:
            return None

        try:
            video_base64 = self.appium_driver.stop_recording_screen()
            if not video_base64:
                return None

            video_bytes = base64.b64decode(video_base64)

            # Use the same directory as the main video
            if self.video_file_path:
                video_dir = os.path.dirname(self.video_file_path)
                partial_path = os.path.join(video_dir, "recording_partial_crash.mp4")
            else:
                # Fallback directory
                video_dir = os.path.join("output_data", "videos")
                os.makedirs(video_dir, exist_ok=True)
                partial_path = os.path.join(video_dir, "recording_partial_crash.mp4")

            with open(partial_path, "wb") as f:
                f.write(video_bytes)

            logger.info(f"Partial video recording saved: {partial_path}")
            return os.path.abspath(partial_path)
        except Exception:
            # Fallback to ADB pull
            return self.manual_pull_video_fallback(0)
        finally:
            self._is_recording = False
    
    def manual_pull_video_fallback(self, run_id: int) -> Optional[str]:
        """Attempt to manually pull the last generated video file from the device using ADB.
        
        This is a fallback for when Appium fails to return the video data (e.g. session crash).
        It looks for recent mp4 files in /sdcard/ created in the last few minutes.
        """
        try:
            # We need device_id
            if not self.appium_driver or not self.appium_driver.device_id:
                logger.warning("Cannot manual pull video: No device_id available")
                return None
            
            device_id = self.appium_driver.device_id
            
            # List mp4 files in /sdcard/, sorted by time (newest first)
            # screenrecord files usually don't have a standard name if initiated by Appium 
            # (Appium often uses a random UUID), but we can guess.
            import subprocess
            
            # Find recent mp4 files
            cmd = ['adb', '-s', device_id, 'shell', 'ls', '-t', '/sdcard/*.mp4']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                return None
                
            files = result.stdout.strip().split('\n')
            if not files or not files[0] or 'No such file' in files[0]:
                return None
            
            # Get the newest file
            latest_video = files[0].strip()
            
            # Validate it looks like a path
            if not latest_video.startswith('/'):
                return None
                
            logger.info(f"Found candidate video file on device: {latest_video}")
            
            # Pull it
            # Determine target path
            if self.video_file_path:
                local_path = self.video_file_path
            else:
                # Fallback path if not set
                video_dir = os.path.join("output_data", "videos")
                os.makedirs(video_dir, exist_ok=True)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                local_path = os.path.join(video_dir, f"fallback_recording_{run_id}_{timestamp}.mp4")
            
            pull_cmd = ['adb', '-s', device_id, 'pull', latest_video, local_path]
            pull_result = subprocess.run(pull_cmd, capture_output=True, text=True, timeout=30)
            
            if pull_result.returncode == 0 and os.path.exists(local_path):
                logger.info(f"Successfully pulled video via ADB fallback: {local_path}")
                # Optional: Delete from device to clean up
                subprocess.run(['adb', '-s', device_id, 'shell', 'rm', latest_video], timeout=5)
                return os.path.abspath(local_path)
            else:
                logger.warning(f"Failed to pull video: {pull_result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error in manual_pull_video_fallback: {e}")
            return None
