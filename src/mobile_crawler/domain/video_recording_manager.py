"""Video recording manager for screen recording during crawls."""

import base64
import os
from typing import Optional

from mobile_crawler.infrastructure.appium_driver import AppiumDriver


class VideoRecordingManager:
    """Manages screen recording using Appium's built-in recording capabilities."""

    def __init__(self, appium_driver: AppiumDriver, session_folder: str):
        """Initialize video recording manager.
        
        Args:
            appium_driver: Appium driver instance
            session_folder: Path to session folder for saving video
        """
        self.appium_driver = appium_driver
        self.session_folder = session_folder
        self.is_recording = False
        self.video_path: Optional[str] = None

    def start(self):
        """Start screen recording."""
        if self.is_recording:
            return
        
        self.appium_driver.driver.start_recording_screen()
        self.is_recording = True

    def stop_and_save(self) -> str:
        """Stop recording and save video to session folder.
        
        Returns:
            Path to the saved video file
            
        Raises:
            RuntimeError: If recording was not started
        """
        if not self.is_recording:
            raise RuntimeError("Recording not started")
        
        # Get base64 encoded video
        video_base64 = self.appium_driver.driver.stop_recording_screen()
        
        # Decode and save
        video_bytes = base64.b64decode(video_base64)
        video_dir = os.path.join(self.session_folder, "video")
        os.makedirs(video_dir, exist_ok=True)
        self.video_path = os.path.join(video_dir, "recording.mp4")
        
        with open(self.video_path, "wb") as f:
            f.write(video_bytes)
        
        self.is_recording = False
        return self.video_path

    def save_partial_on_crash(self):
        """Attempt to save partial recording on crash.
        
        This method can be called in exception handlers to save
        any available recording data.
        """
        if not self.is_recording:
            return
        
        try:
            video_base64 = self.appium_driver.driver.stop_recording_screen()
            video_bytes = base64.b64decode(video_base64)
            video_dir = os.path.join(self.session_folder, "video")
            os.makedirs(video_dir, exist_ok=True)
            partial_path = os.path.join(video_dir, "recording_partial.mp4")
            
            with open(partial_path, "wb") as f:
                f.write(video_bytes)
            
            self.video_path = partial_path
        except Exception:
            # If saving fails, just stop recording flag
            pass
        finally:
            self.is_recording = False