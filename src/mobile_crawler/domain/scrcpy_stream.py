"""Live Feed video source: talks to a vendored scrcpy server over adb.

Pushes the pinned ``scrcpy-server`` jar with the project's own adb, forwards
its socket, and decodes the raw H.264 stream into RGB frames. Works for USB and
wireless adb serials alike because everything goes through ``adb -s <serial>``.
See docs/adr/0004-drive-vendored-scrcpy-server-directly.md.
"""

import logging
import re
import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import av
import numpy as np

logger = logging.getLogger(__name__)

# Bumping this means replacing the jar too: the server refuses to start when
# the version argument does not match the jar it was built as.
SERVER_VERSION = "3.3.4"
SERVER_JAR = Path(__file__).resolve().parent.parent / "resources" / "scrcpy" / f"scrcpy-server-v{SERVER_VERSION}.jar"
DEVICE_JAR_PATH = f"/data/local/tmp/mobile-crawler-scrcpy-{SERVER_VERSION}.jar"

DEFAULT_MAX_SIZE = 720
DEFAULT_MAX_FPS = 15
_CONNECT_TIMEOUT_S = 8.0
_ADB_TIMEOUT_S = 15


class ScrcpyStreamError(RuntimeError):
    """The live feed could not be started or died."""


def build_server_args(scid: int, max_size: int, max_fps: int) -> list[str]:
    """Server arguments for a video-only, raw H.264, forward-tunnel session."""
    return [
        SERVER_VERSION,
        f"scid={scid:08x}",
        "log_level=info",
        "audio=false",
        "control=false",
        "video_codec=h264",
        f"max_size={max_size}",
        f"max_fps={max_fps}",
        "raw_stream=true",
        "tunnel_forward=true",
        "cleanup=false",
        "power_on=false",
    ]


def parse_wm_size(output: str) -> tuple[int, int] | None:
    """Parse ``adb shell wm size`` output. An Override size wins over Physical."""
    matches = re.findall(r"(Physical|Override) size:\s*(\d+)x(\d+)", output)
    if not matches:
        return None
    by_kind = {kind: (int(w), int(h)) for kind, w, h in matches}
    return by_kind.get("Override") or by_kind.get("Physical")


class H264Decoder:
    """Incremental raw H.264 decoder returning RGB ndarrays."""

    def __init__(self) -> None:
        self._ctx = av.CodecContext.create("h264", "r")

    def feed(self, data: bytes) -> np.ndarray | None:
        """Decode a chunk; returns only the newest frame so the view never lags."""
        latest = None
        try:
            for packet in self._ctx.parse(data):
                for frame in self._ctx.decode(packet):
                    latest = frame
        except av.error.FFmpegError as exc:
            logger.debug("Live feed decode error (skipping chunk): %s", exc)
            return None
        if latest is None:
            return None
        return np.ascontiguousarray(latest.to_ndarray(format="rgb24"))


class ScrcpyStream:
    """One live-feed session against one device serial."""

    def __init__(
        self,
        adb_path: str,
        serial: str,
        max_size: int = DEFAULT_MAX_SIZE,
        max_fps: int = DEFAULT_MAX_FPS,
    ) -> None:
        self._adb = adb_path
        self._serial = serial
        self._max_size = max_size
        self._max_fps = max_fps
        self._scid = int(time.time() * 1000) & 0x7FFFFFFF
        self._port: int | None = None
        self._server: subprocess.Popen | None = None
        self._sock: socket.socket | None = None
        self._first_chunk = b""
        self._stopped = False

    def _adb_cmd(self, *args: str) -> list[str]:
        return [self._adb, "-s", self._serial, *args]

    def _run_adb(self, *args: str) -> str:
        try:
            result = subprocess.run(
                self._adb_cmd(*args),
                capture_output=True,
                text=True,
                timeout=_ADB_TIMEOUT_S,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ScrcpyStreamError(f"adb {args[0]} failed: {exc}") from exc
        if result.returncode != 0:
            raise ScrcpyStreamError(f"adb {args[0]} failed: {(result.stderr or result.stdout).strip()}")
        return result.stdout

    def device_size(self) -> tuple[int, int] | None:
        """Device screen size in pixels (natural orientation), or None."""
        try:
            return parse_wm_size(self._run_adb("shell", "wm", "size"))
        except ScrcpyStreamError:
            return None

    def start(self) -> None:
        if not SERVER_JAR.is_file():
            raise ScrcpyStreamError(f"scrcpy server jar missing: {SERVER_JAR}")
        self._run_adb("push", str(SERVER_JAR), DEVICE_JAR_PATH)

        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            self._port = probe.getsockname()[1]
        self._run_adb("forward", f"tcp:{self._port}", f"localabstract:scrcpy_{self._scid:08x}")

        server_args = " ".join(build_server_args(self._scid, self._max_size, self._max_fps))
        self._server = subprocess.Popen(
            self._adb_cmd(
                "shell",
                f"CLASSPATH={DEVICE_JAR_PATH} app_process / " f"com.genymobile.scrcpy.Server {server_args}",
            ),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._sock = self._connect()

    def _connect(self) -> socket.socket:
        """Connect to the forwarded port, retrying until the server is listening.

        adb accepts the TCP connection before the server has opened its
        socket, so "connected" only counts once a first byte arrives.
        """
        deadline = time.monotonic() + _CONNECT_TIMEOUT_S
        while time.monotonic() < deadline and not self._stopped:
            if self._server is not None and self._server.poll() is not None:
                raise ScrcpyStreamError("scrcpy server exited during startup")
            sock = socket.socket()
            sock.settimeout(1.0)
            try:
                sock.connect(("127.0.0.1", self._port))
                first = sock.recv(65536)
                if first:
                    self._first_chunk = first
                    return sock
            except OSError:
                pass
            sock.close()
            time.sleep(0.2)
        raise ScrcpyStreamError("timed out waiting for the scrcpy server")

    def frames(self) -> Iterator[np.ndarray]:
        """Yield decoded RGB frames until the stream ends or stop() is called."""
        if self._sock is None:
            raise ScrcpyStreamError("stream not started")
        decoder = H264Decoder()
        chunk = self._first_chunk
        while not self._stopped:
            frame = decoder.feed(chunk)
            if frame is not None:
                yield frame
            try:
                chunk = self._sock.recv(65536)
            except TimeoutError:
                chunk = b""
                continue
            except OSError:
                break
            if not chunk:
                break
        if not self._stopped:
            raise ScrcpyStreamError("device stream ended")

    def stop(self) -> None:
        self._stopped = True
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
        if self._server is not None and self._server.poll() is None:
            self._server.terminate()
        if self._port is not None:
            try:
                subprocess.run(
                    self._adb_cmd("forward", "--remove", f"tcp:{self._port}"),
                    capture_output=True,
                    timeout=_ADB_TIMEOUT_S,
                )
            except (OSError, subprocess.TimeoutExpired):
                logger.debug("Could not remove live feed adb forward", exc_info=True)
