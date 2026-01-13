"""Tests for video recording manager."""

import base64
import os
import tempfile
from unittest.mock import Mock, MagicMock, patch

import pytest

from mobile_crawler.domain.video_recording_manager import VideoRecordingManager


class TestVideoRecordingManager:
    """Test suite for VideoRecordingManager."""
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock config manager."""
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "enable_video_recording": True,
            "app_package": "com.test.app",
            "VIDEO_RECORDING_DIR": "/tmp/videos",
        }.get(key, default)
        return config
    
    @pytest.fixture
    def mock_config_manager_disabled(self):
        """Create a mock config manager with recording disabled."""
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "enable_video_recording": False,
            "app_package": "com.test.app",
        }.get(key, default)
        return config
    
    @pytest.fixture
    def mock_appium_driver(self):
        """Create a mock Appium driver."""
        driver = Mock()
        driver.start_recording_screen.return_value = True
        driver.stop_recording_screen.return_value = base64.b64encode(b"dummy video data").decode('utf-8')
        return driver
    
    def test_init_with_recording_enabled(self, mock_appium_driver, mock_config_manager):
        """Test initialization with video recording enabled."""
        manager = VideoRecordingManager(
            appium_driver=mock_appium_driver,
            config_manager=mock_config_manager,
        )
        
        assert manager.video_recording_enabled is True
        assert manager._is_recording is False
        assert manager.video_file_path is None
    
    def test_init_with_recording_disabled(self, mock_appium_driver, mock_config_manager_disabled):
        """Test initialization with video recording disabled."""
        manager = VideoRecordingManager(
            appium_driver=mock_appium_driver,
            config_manager=mock_config_manager_disabled,
        )
        
        assert manager.video_recording_enabled is False
    
    def test_start_recording_when_enabled(self, mock_appium_driver, mock_config_manager):
        """Test starting screen recording when enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = VideoRecordingManager(
                appium_driver=mock_appium_driver,
                config_manager=mock_config_manager,
            )
            
            result = manager.start_recording(run_id=1, step_num=1, session_path=temp_dir)
            
            assert result is True
            assert manager._is_recording is True
            mock_appium_driver.start_recording_screen.assert_called_once()
    
    def test_start_recording_when_disabled(self, mock_appium_driver, mock_config_manager_disabled):
        """Test that start_recording returns False when disabled."""
        manager = VideoRecordingManager(
            appium_driver=mock_appium_driver,
            config_manager=mock_config_manager_disabled,
        )
        
        result = manager.start_recording(run_id=1, step_num=1)
        
        assert result is False
        mock_appium_driver.start_recording_screen.assert_not_called()
    
    def test_start_recording_when_already_recording(self, mock_appium_driver, mock_config_manager):
        """Test starting when already recording returns True without calling driver again."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = VideoRecordingManager(
                appium_driver=mock_appium_driver,
                config_manager=mock_config_manager,
            )
            manager._is_recording = True
            
            result = manager.start_recording(run_id=1, step_num=1, session_path=temp_dir)
            
            # Should return True but not call driver again
            assert result is True
            mock_appium_driver.start_recording_screen.assert_not_called()
    
    def test_stop_and_save_success(self, mock_appium_driver, mock_config_manager):
        """Test stopping and saving recording successfully."""
        dummy_video = b"dummy video data"
        encoded_video = base64.b64encode(dummy_video).decode('utf-8')
        mock_appium_driver.stop_recording_screen.return_value = encoded_video
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = VideoRecordingManager(
                appium_driver=mock_appium_driver,
                config_manager=mock_config_manager,
            )
            # First start recording
            manager.start_recording(run_id=1, step_num=1, session_path=temp_dir)
            
            # Then stop and save
            video_path = manager.stop_recording_and_save()
            
            assert manager._is_recording is False
            assert video_path is not None
            assert video_path.endswith(".mp4")
            assert os.path.exists(video_path)
            
            # Verify content
            with open(video_path, "rb") as f:
                saved_data = f.read()
            assert saved_data == dummy_video
    
    def test_stop_without_start_returns_none(self, mock_appium_driver, mock_config_manager):
        """Test stopping without starting returns None."""
        manager = VideoRecordingManager(
            appium_driver=mock_appium_driver,
            config_manager=mock_config_manager,
        )
        
        result = manager.stop_recording_and_save()
        
        assert result is None
    
    def test_is_recording_property(self, mock_appium_driver, mock_config_manager):
        """Test is_recording property returns correct state."""
        manager = VideoRecordingManager(
            appium_driver=mock_appium_driver,
            config_manager=mock_config_manager,
        )
        
        assert manager.is_recording() is False
        
        manager._is_recording = True
        assert manager.is_recording() is True
    
    def test_save_partial_on_crash(self, mock_appium_driver, mock_config_manager):
        """Test saving partial recording on crash."""
        dummy_video = b"partial video data"
        encoded_video = base64.b64encode(dummy_video).decode('utf-8')
        mock_appium_driver.stop_recording_screen.return_value = encoded_video
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = VideoRecordingManager(
                appium_driver=mock_appium_driver,
                config_manager=mock_config_manager,
            )
            # Start recording first
            manager.start_recording(run_id=1, step_num=1, session_path=temp_dir)
            
            # Save partial on crash
            manager.save_partial_on_crash()
            
            assert manager._is_recording is False
    
    def test_save_partial_on_crash_exception_handling(self, mock_appium_driver, mock_config_manager):
        """Test partial save handles exceptions gracefully."""
        mock_appium_driver.stop_recording_screen.side_effect = Exception("Recording failed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = VideoRecordingManager(
                appium_driver=mock_appium_driver,
                config_manager=mock_config_manager,
            )
            # Start recording first
            manager._is_recording = True
            manager.video_file_path = os.path.join(temp_dir, "test.mp4")
            
            # Should not raise exception
            manager.save_partial_on_crash()
            
            assert manager._is_recording is False