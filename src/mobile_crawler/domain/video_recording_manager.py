"""ADB-backed segmented video recording for crawl sessions."""

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from mobile_crawler.config.config_manager import ConfigManager
    from mobile_crawler.infrastructure.adb_client import ADBClient

logger = logging.getLogger(__name__)


@dataclass
class VideoSegment:
    """Metadata for one pulled screenrecord segment."""

    part: int
    device_path: str
    local_path: str | None
    started_at: str
    stopped_at: str | None = None
    size_bytes: int = 0
    error: str | None = None


class VideoRecordingManager:
    """Records Android screen videos using segmented ADB screenrecord."""

    def __init__(
        self,
        config_manager: "ConfigManager",
        adb_client: Optional["ADBClient"] = None,
        device_id: str | None = None,
    ) -> None:
        self.config_manager = config_manager
        self.adb_client = adb_client
        self.device_id = device_id
        self.video_recording_enabled = bool(
            config_manager.get("enable_video_recording", False)
        )
        self.adb_executable = str(config_manager.get("adb_executable_path", "adb"))
        self.segment_seconds = int(
            config_manager.get("video_recording_segment_seconds", 180) or 180
        )
        self.segment_seconds = max(1, min(self.segment_seconds, 180))
        self.finalize_wait = float(
            config_manager.get("video_recording_finalize_wait", 1.0) or 0.0
        )
        self.device_dir = str(
            config_manager.get(
                "video_recording_device_dir", "/sdcard/mobile-crawler/videos"
            )
        ).rstrip("/")

        self.run_id: int | None = None
        self.app_package: str = ""
        self.session_path: str | None = None
        self.video_dir: Path | None = None
        self.manifest_path: Path | None = None

        self._process: asyncio.subprocess.Process | None = None
        self._segment_task: asyncio.Task | None = None
        self._stop_requested = asyncio.Event()
        self._part = 0
        self._current_segment: VideoSegment | None = None
        self._segments: list[VideoSegment] = []
        self._recording = False

    def is_recording(self) -> bool:
        """Return whether this manager currently owns an active recording."""
        return self._recording

    async def start_recording_async(
        self, run_id: int, session_path: str, app_package: str
    ) -> tuple[bool, str]:
        """Start segmented recording in a background task."""
        if not self.video_recording_enabled:
            return False, "Video recording is not enabled"
        if self._recording:
            return True, "Video recording already started"

        self.run_id = run_id
        self.session_path = session_path
        self.app_package = app_package
        self.video_dir = Path(session_path) / "videos"
        self.video_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.video_dir / "manifest.json"
        self._stop_requested = asyncio.Event()
        self._segments = []
        self._part = 0

        output, retcode = await self._run_adb_command_async(
            ["shell", "mkdir", "-p", self.device_dir],
            suppress_stderr=True,
        )
        if retcode != 0:
            message = f"Failed to create device video directory: {output}"
            logger.warning(message)
            await self._write_manifest_async()
            return False, message

        try:
            await self._start_next_segment()
        except Exception as exc:
            message = f"Failed to start video recording: {exc}"
            logger.warning(message)
            await self._write_manifest_async()
            return False, message

        self._recording = True
        self._segment_task = asyncio.create_task(self._segment_loop())
        logger.info("Video recording started")
        await self._write_manifest_async()
        return True, "Video recording started"

    async def stop_recording_and_save_async(self) -> str | None:
        """Stop recording, pull the active segment, and write the manifest."""
        if not self._recording and not self._process:
            await self._write_manifest_async()
            return None

        self._stop_requested.set()
        await self._stop_current_process()

        if self._segment_task:
            try:
                await asyncio.wait_for(self._segment_task, timeout=30.0)
            except TimeoutError:
                logger.warning("Timed out waiting for video segment task to stop")
            finally:
                self._segment_task = None

        if self._current_segment:
            await self._pull_current_segment()

        self._recording = False
        await self._write_manifest_async()

        saved_segments = [segment.local_path for segment in self._segments if segment.local_path]
        if saved_segments:
            logger.info("Video recording saved: %s", saved_segments[-1])
            return saved_segments[-1]
        return None

    async def save_partial_on_crash_async(self) -> str | None:
        """Best-effort stop/pull for exception paths."""
        return await self.stop_recording_and_save_async()

    async def _segment_loop(self) -> None:
        while not self._stop_requested.is_set():
            process = self._process
            if process is None:
                return

            await process.wait()
            if self._current_segment:
                await self._pull_current_segment()

            if not self._stop_requested.is_set():
                try:
                    await self._start_next_segment()
                except Exception as exc:
                    logger.warning("Failed to roll video recording segment: %s", exc)
                    self._recording = False
                    await self._write_manifest_async()
                    return

    async def _start_next_segment(self) -> None:
        self._part += 1
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        sanitized_package = re.sub(r"[^\w.-]+", "_", self.app_package).replace(".", "_")
        filename = (
            f"{sanitized_package}_run{self.run_id}_part{self._part:03d}_{timestamp}.mp4"
        )
        device_path = f"{self.device_dir}/{filename}"

        args = self._adb_base_args() + [
            "shell",
            "screenrecord",
            "--time-limit",
            str(self.segment_seconds),
            device_path,
        ]

        self._current_segment = VideoSegment(
            part=self._part,
            device_path=device_path,
            local_path=str(self.video_dir / filename) if self.video_dir else None,
            started_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )
        self._process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        logger.debug("Started video segment %s at %s", self._part, device_path)

    async def _stop_current_process(self) -> None:
        process = self._process
        if process is None or process.returncode is not None:
            return

        await self._run_adb_command_async(
            ["shell", "pkill", "-2", "screenrecord"],
            suppress_stderr=True,
            timeout=5.0,
        )
        try:
            await asyncio.wait_for(process.wait(), timeout=10.0)
        except TimeoutError:
            logger.warning("screenrecord did not stop after SIGINT; terminating adb process")
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except TimeoutError:
                process.kill()
                await process.wait()

    async def _pull_current_segment(self) -> None:
        segment = self._current_segment
        if not segment:
            return

        segment.stopped_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        if self.finalize_wait > 0:
            await asyncio.sleep(self.finalize_wait)

        local_path = segment.local_path
        if not local_path:
            segment.error = "Local segment path not set"
            self._segments.append(segment)
            self._current_segment = None
            await self._write_manifest_async()
            return

        output, retcode = await self._run_adb_command_async(
            ["shell", "test", "-f", segment.device_path],
            suppress_stderr=True,
        )
        if retcode != 0:
            segment.error = f"Device video file not found: {output}".strip()
            logger.warning(segment.error)
            self._segments.append(segment)
            self._current_segment = None
            await self._write_manifest_async()
            return

        output, retcode = await self._run_adb_command_async(
            ["pull", segment.device_path, local_path],
        )
        if retcode != 0:
            segment.error = f"Failed to pull video segment: {output}".strip()
            logger.warning(segment.error)
            self._segments.append(segment)
            self._current_segment = None
            await self._write_manifest_async()
            return

        if os.path.exists(local_path):
            segment.size_bytes = os.path.getsize(local_path)
            segment.local_path = os.path.abspath(local_path)
            await self._run_adb_command_async(
                ["shell", "rm", segment.device_path],
                suppress_stderr=True,
            )
            logger.info("Video segment saved: %s", segment.local_path)
        else:
            segment.error = f"ADB pull succeeded but local file is missing: {local_path}"
            logger.warning(segment.error)

        self._segments.append(segment)
        self._current_segment = None
        await self._write_manifest_async()

    async def _write_manifest_async(self) -> None:
        if not self.manifest_path:
            return

        payload = {
            "run_id": self.run_id,
            "package": self.app_package,
            "device_id": self.device_id,
            "segment_seconds": self.segment_seconds,
            "segments": [asdict(segment) for segment in self._segments],
        }
        if self._current_segment:
            payload["active_segment"] = asdict(self._current_segment)

        await asyncio.to_thread(
            self.manifest_path.write_text,
            json.dumps(payload, indent=2),
            "utf-8",
        )

    async def _run_adb_command_async(
        self,
        command_list: list[str],
        suppress_stderr: bool = False,
        timeout: float | None = None,
    ) -> tuple[str, int]:
        if self.adb_client:
            try:
                return await self.adb_client.execute_async(
                    self._device_command(command_list),
                    suppress_stderr=suppress_stderr,
                    timeout=timeout,
                )
            except TypeError:
                return await self.adb_client.execute_async(
                    self._device_command(command_list),
                    suppress_stderr=suppress_stderr,
                )

        from mobile_crawler.infrastructure.adb_client import ADBClient

        temp_client = ADBClient(adb_executable=self.adb_executable, timeout=timeout or 30.0)
        return await temp_client.execute_async(
            self._device_command(command_list),
            suppress_stderr=suppress_stderr,
            timeout=timeout,
        )

    def _adb_base_args(self) -> list[str]:
        args = [self.adb_executable]
        if self.device_id:
            args.extend(["-s", self.device_id])
        return args

    def _device_command(self, command_list: list[str]) -> list[str]:
        if self.device_id:
            return ["-s", self.device_id] + command_list
        return command_list
