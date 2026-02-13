"""Video recording manager for screen recording during crawls."""

import base64
import logging
import os
import time
from typing import TYPE_CHECKING, Optional

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
    ) -> bool:
        """Starts video recording.

        Args:
            run_id: Optional run ID for filename generation
            step_num: Optional step number for filename generation
            session_path: Optional session directory path for output

        Returns:
            True if recording started successfully, False otherwise
        """
        logger.info(f"start_recording called: video_recording_enabled={self.video_recording_enabled}, run_id={run_id}, session_path={session_path}")
        logger.debug(f"[DEBUG] VideoRecordingManager.start_recording - enabled={self.video_recording_enabled}, run_id={run_id}, step_num={step_num}, session_path={session_path}")
        
        if not self.video_recording_enabled:
            logger.warning("Video recording is not enabled in VideoRecordingManager, skipping start")
            logger.debug("[DEBUG] Video recording disabled in config, aborting start_recording")
            return False

        if self._is_recording:
            logger.warning("Video recording already started by this manager.")
            logger.debug("[DEBUG] Video recording already active, returning True")
            return True

        try:
            # Check if AppiumDriver is available
            if not self.appium_driver:
                logger.error("AppiumDriver not available, cannot start video recording")
                logger.debug("[DEBUG] AppiumDriver is None")
                return False
            
            logger.debug(f"[DEBUG] AppiumDriver available: {self.appium_driver is not None}")
            
            # Check if driver instance exists
            driver = getattr(self.appium_driver, '_driver', None)
            if driver is None:
                logger.error("Appium WebDriver instance not available, cannot start video recording")
                logger.debug("[DEBUG] AppiumDriver._driver is None - driver may not be connected")
                return False
            
            logger.debug(f"[DEBUG] Appium WebDriver instance available: {driver is not None}")
            logger.debug(f"[DEBUG] Appium WebDriver session_id: {getattr(driver, 'session_id', 'N/A')}")

            # Generate filename
            target_app_package = str(self.config_manager.get("app_package", ""))
            if not target_app_package:
                logger.error("APP_PACKAGE not configured, cannot start video recording")
                logger.debug("[DEBUG] APP_PACKAGE is empty or not set in config")
                return False
            
            logger.debug(f"[DEBUG] App package: {target_app_package}")

            sanitized_package = target_app_package.replace(".", "_")
            timestamp = time.strftime("%Y%m%d_%H%M%S")

            if run_id is not None and step_num is not None:
                video_filename = (
                    f"{sanitized_package}_run{run_id}_step{step_num}_{timestamp}.mp4"
                )
            else:
                video_filename = f"{sanitized_package}_{timestamp}.mp4"

            # Resolve output directory - videos are saved to "videos" folder in session directory
            if session_path:
                video_output_dir = os.path.join(session_path, "videos")
            elif self.session_folder_manager and run_id:
                # Try to get session path from manager
                from mobile_crawler.infrastructure.run_repository import RunRepository
                from mobile_crawler.infrastructure.database import DatabaseManager

                db_manager = DatabaseManager()
                run_repo = RunRepository(db_manager)
                run = run_repo.get_run_by_id(run_id)
                if run and self.session_folder_manager:
                    video_output_dir = self.session_folder_manager.get_subfolder(run, "videos")
                else:
                    video_output_dir = os.path.join("output_data", "videos")
            else:
                video_output_dir = os.path.join("output_data", "videos")

            os.makedirs(video_output_dir, exist_ok=True)
            logger.debug(f"[DEBUG] Video output directory: {video_output_dir}")
            logger.debug(f"[DEBUG] Video output directory exists: {os.path.exists(video_output_dir)}")

            # Set the full path (we'll save here when stopping)
            self.video_file_path = os.path.join(video_output_dir, video_filename)
            logger.debug(f"[DEBUG] Video file path: {self.video_file_path}")

            # Start recording using Appium's built-in method
            logger.debug("[DEBUG] Calling appium_driver.start_recording_screen()...")
            success = False
            for attempt in range(2):  # Retry once
                try:
                    success = self.appium_driver.start_recording_screen()
                    logger.debug(f"[DEBUG] start_recording_screen() attempt {attempt+1} returned: {success}")
                    if success:
                        break
                except Exception as e:
                    logger.error(f"[DEBUG] Exception in start_recording_screen() attempt {attempt+1}: {e}", exc_info=True)
                    if attempt == 0:  # Only retry on first attempt
                        logger.debug("[DEBUG] Retrying start_recording_screen()...")
                        time.sleep(1.0)  # Brief pause before retry
                        continue
                    else:
                        break
            
            if not success:
                self.video_file_path = None
                self._is_recording = False
                return False

        except Exception as e:
            logger.error(f"Error starting video recording: {e}", exc_info=True)
            self.video_file_path = None
            self._is_recording = False
            return False

    def stop_recording_and_save(self) -> Optional[str]:
        """Stops video recording and saves the file.

        Returns:
            Path to saved video file, or None on error
        """
        logger.debug("[DEBUG] VideoRecordingManager.stop_recording_and_save() called")
        logger.debug(f"[DEBUG] video_recording_enabled={self.video_recording_enabled}, _is_recording={self._is_recording}")
        
        if not self.video_recording_enabled:
            logger.debug("[DEBUG] Video recording disabled, returning None")
            return None

        if not self._is_recording:
            logger.warning(
                "Video recording not started by this manager. Cannot stop/save."
            )
            logger.debug("[DEBUG] Video recording was not started, cannot stop")
            return None

        try:
            # Stop recording and get video data (base64 string)
            logger.debug("[DEBUG] Calling appium_driver.stop_recording_screen()...")
            video_base64 = self.appium_driver.stop_recording_screen()
            self._is_recording = False
            logger.debug(f"[DEBUG] stop_recording_screen() returned: {video_base64 is not None}")
            logger.debug(f"[DEBUG] Video data length: {len(video_base64) if video_base64 else 0} characters")

            if not video_base64:
                logger.error("Video recording stopped but no data returned")
                logger.debug("[DEBUG] No video data received from Appium driver")
                self.video_file_path = None
                return None

            if not self.video_file_path:
                logger.error("Video file path not set. Cannot save.")
                return None

            # Decode base64 and save to file
            try:
                video_bytes = base64.b64decode(video_base64)
            except Exception as e:
                logger.error(f"Failed to decode base64 video data: {e}")
                self.video_file_path = None
                return None

            # Ensure directory exists
            os.makedirs(os.path.dirname(self.video_file_path), exist_ok=True)

            # Save video to file
            with open(self.video_file_path, "wb") as f:
                f.write(video_bytes)

            if os.path.exists(self.video_file_path):
                file_size = os.path.getsize(self.video_file_path)
                if file_size > 0:
                    saved_path = os.path.abspath(self.video_file_path)
                    logger.info(f"Video recording saved: {saved_path} ({file_size} bytes)")
                    self.video_file_path = None  # Reset after successful save
                    return saved_path
                else:
                    logger.warning(
                        f"Video file saved but is EMPTY: {self.video_file_path}"
                    )
                    return os.path.abspath(self.video_file_path)
            else:
                logger.error(
                    f"Failed to save video recording to: {self.video_file_path}"
                )
                self.video_file_path = None
                return None

        except Exception as e:
            logger.error(f"Error stopping/saving video recording: {e}", exc_info=True)
            self._is_recording = False
            self.video_file_path = None
            return None

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
                partial_path = os.path.join(video_dir, "recording_partial.mp4")
            else:
                # Fallback directory
                video_dir = os.path.join("output_data", "videos")
                os.makedirs(video_dir, exist_ok=True)
                partial_path = os.path.join(video_dir, "recording_partial.mp4")

            with open(partial_path, "wb") as f:
                f.write(video_bytes)

            self.video_file_path = partial_path
            logger.info(f"Partial video recording saved: {partial_path}")
            return os.path.abspath(partial_path)
        except Exception as e:
            logger.error(f"Error saving partial video recording: {e}", exc_info=True)
            return None
        finally:
            self._is_recording = False
