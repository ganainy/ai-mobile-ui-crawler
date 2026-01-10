"""Tests for video recording manager."""

import base64
import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from mobile_crawler.domain.video_recording_manager import VideoRecordingManager


class TestVideoRecordingManager:
    def test_start_recording(self):
        """Test starting screen recording."""
        mock_driver = Mock()
        manager = VideoRecordingManager(mock_driver, "/tmp/session")
        
        manager.start()
        
        assert manager.is_recording
        mock_driver.driver.start_recording_screen.assert_called_once()

    def test_start_already_recording(self):
        """Test starting when already recording does nothing."""
        mock_driver = Mock()
        manager = VideoRecordingManager(mock_driver, "/tmp/session")
        manager.is_recording = True
        
        manager.start()
        
        # Should not call start again
        mock_driver.driver.start_recording_screen.assert_not_called()

    def test_stop_and_save_success(self):
        """Test stopping and saving recording successfully."""
        mock_driver = Mock()
        # Mock base64 encoded video (small dummy data)
        dummy_video = b"dummy video data"
        encoded_video = base64.b64encode(dummy_video).decode('utf-8')
        mock_driver.driver.stop_recording_screen.return_value = encoded_video
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = VideoRecordingManager(mock_driver, temp_dir)
            manager.is_recording = True
            
            video_path = manager.stop_and_save()
            
            assert not manager.is_recording
            assert video_path.endswith("recording.mp4")
            assert os.path.exists(video_path)
            
            # Verify content
            with open(video_path, "rb") as f:
                saved_data = f.read()
            assert saved_data == dummy_video

    def test_stop_without_start_raises_error(self):
        """Test stopping without starting raises error."""
        mock_driver = Mock()
        manager = VideoRecordingManager(mock_driver, "/tmp/session")
        
        with pytest.raises(RuntimeError, match="Recording not started"):
            manager.stop_and_save()

    def test_save_partial_on_crash(self):
        """Test saving partial recording on crash."""
        mock_driver = Mock()
        dummy_video = b"partial video data"
        encoded_video = base64.b64encode(dummy_video).decode('utf-8')
        mock_driver.driver.stop_recording_screen.return_value = encoded_video
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = VideoRecordingManager(mock_driver, temp_dir)
            manager.is_recording = True
            
            manager.save_partial_on_crash()
            
            assert not manager.is_recording
            partial_path = os.path.join(temp_dir, "video", "recording_partial.mp4")
            assert os.path.exists(partial_path)
            
            with open(partial_path, "rb") as f:
                saved_data = f.read()
            assert saved_data == dummy_video

    def test_save_partial_on_crash_exception_handling(self):
        """Test partial save handles exceptions gracefully."""
        mock_driver = Mock()
        mock_driver.driver.stop_recording_screen.side_effect = Exception("Recording failed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = VideoRecordingManager(mock_driver, temp_dir)
            manager.is_recording = True
            
            # Should not raise exception
            manager.save_partial_on_crash()
            
            assert not manager.is_recording
            # No file should be created due to exception
            partial_path = os.path.join(temp_dir, "video", "recording_partial.mp4")
            assert not os.path.exists(partial_path)