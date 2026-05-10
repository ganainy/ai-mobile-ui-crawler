"""Tests for ADB-backed video recording manager."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from mobile_crawler.domain.video_recording_manager import VideoRecordingManager


def _config(enabled=True):
    config = Mock()
    values = {
        "enable_video_recording": enabled,
        "adb_executable_path": "adb",
        "video_recording_segment_seconds": 180,
        "video_recording_finalize_wait": 0.0,
        "video_recording_device_dir": "/sdcard/mobile-crawler/videos",
    }
    config.get.side_effect = lambda key, default=None: values.get(key, default)
    return config


def test_disabled_recording_skips_adb(tmp_path):
    adb_client = Mock()
    adb_client.execute_async = AsyncMock()
    manager = VideoRecordingManager(_config(enabled=False), adb_client=adb_client, device_id="dev1")

    success, message = asyncio.run(
        manager.start_recording_async(1, str(tmp_path), "com.test.app")
    )

    assert success is False
    assert "not enabled" in message
    adb_client.execute_async.assert_not_called()


@patch("mobile_crawler.domain.video_recording_manager.asyncio.create_subprocess_exec")
def test_start_recording_starts_first_segment(mock_create_process, tmp_path):
    process = Mock()
    process.returncode = None
    process.wait = AsyncMock(return_value=0)
    mock_create_process.return_value = process

    adb_client = Mock()
    adb_client.execute_async = AsyncMock(return_value=("", 0))
    manager = VideoRecordingManager(_config(), adb_client=adb_client, device_id="dev1")

    async def run_lifecycle():
        success, message = await manager.start_recording_async(42, str(tmp_path), "com.test.app")
        recording_after_start = manager.is_recording()
        await manager.stop_recording_and_save_async()
        return success, message, recording_after_start

    success, message, recording_after_start = asyncio.run(run_lifecycle())

    assert success is True
    assert "started" in message
    assert recording_after_start is True
    mock_create_process.assert_called_once()
    args = mock_create_process.call_args.args
    assert args[:4] == ("adb", "-s", "dev1", "shell")
    assert "screenrecord" in args
    assert "--time-limit" in args


@patch("mobile_crawler.domain.video_recording_manager.asyncio.create_subprocess_exec")
def test_stop_pulls_segment_and_writes_manifest(mock_create_process, tmp_path):
    process = Mock()
    process.returncode = None
    process.wait = AsyncMock(return_value=0)
    mock_create_process.return_value = process

    async def adb_side_effect(cmd, suppress_stderr=False, timeout=None):
        device_cmd = cmd[2:] if cmd[:2] == ["-s", "dev1"] else cmd
        if device_cmd[:3] == ["shell", "mkdir", "-p"]:
            return ("", 0)
        if device_cmd[:2] == ["shell", "pkill"]:
            return ("", 0)
        if device_cmd[:2] == ["shell", "test"]:
            return ("", 0)
        if device_cmd and device_cmd[0] == "pull":
            Path(device_cmd[2]).write_bytes(b"mp4-data")
            return ("", 0)
        if device_cmd[:2] == ["shell", "rm"]:
            return ("", 0)
        return ("", 0)

    adb_client = Mock()
    adb_client.execute_async = AsyncMock(side_effect=adb_side_effect)
    manager = VideoRecordingManager(_config(), adb_client=adb_client, device_id="dev1")

    async def run_lifecycle():
        await manager.start_recording_async(42, str(tmp_path), "com.test.app")
        return await manager.stop_recording_and_save_async()

    result = asyncio.run(run_lifecycle())

    assert result is not None
    videos_dir = tmp_path / "videos"
    mp4_files = list(videos_dir.glob("*.mp4"))
    assert len(mp4_files) == 1
    assert mp4_files[0].read_bytes() == b"mp4-data"

    manifest = json.loads((videos_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_id"] == 42
    assert manifest["package"] == "com.test.app"
    assert len(manifest["segments"]) == 1
    assert manifest["segments"][0]["part"] == 1


@patch("mobile_crawler.domain.video_recording_manager.asyncio.create_subprocess_exec")
def test_start_failure_is_graceful(mock_create_process, tmp_path):
    mock_create_process.side_effect = OSError("adb unavailable")
    adb_client = Mock()
    adb_client.execute_async = AsyncMock(return_value=("", 0))
    manager = VideoRecordingManager(_config(), adb_client=adb_client, device_id="dev1")

    success, message = asyncio.run(
        manager.start_recording_async(1, str(tmp_path), "com.test.app")
    )

    assert success is False
    assert "failed" in message.lower()
    assert manager.is_recording() is False
