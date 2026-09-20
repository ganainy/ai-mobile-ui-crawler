"""Background thread that feeds the Live Feed board with decoded device frames."""

import logging

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from mobile_crawler.domain.scrcpy_stream import ScrcpyStream, ScrcpyStreamError

logger = logging.getLogger(__name__)


class LiveFeedWorker(QThread):
    """Streams one device's screen; any failure is reported, never raised.

    A dead feed must never affect the crawl, so every error ends up in
    ``failed`` and the thread simply exits.
    """

    frame_ready = Signal(QImage)
    device_size = Signal(int, int)
    failed = Signal(str)

    def __init__(self, adb_path: str, serial: str, parent=None) -> None:
        super().__init__(parent)
        self._adb_path = adb_path
        self._serial = serial
        self._stream: ScrcpyStream | None = None

    @property
    def serial(self) -> str:
        return self._serial

    def run(self) -> None:
        stream = ScrcpyStream(self._adb_path, self._serial)
        self._stream = stream
        try:
            size = stream.device_size()
            if size:
                self.device_size.emit(*size)
            stream.start()
            for frame in stream.frames():
                height, width, _ = frame.shape
                image = QImage(frame.data, width, height, width * 3, QImage.Format.Format_RGB888)
                self.frame_ready.emit(image.copy())
        except ScrcpyStreamError as exc:
            if not self.isInterruptionRequested():
                logger.warning("Live feed stopped: %s", exc)
                self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001 - feed must never crash the app
            logger.exception("Live feed crashed")
            self.failed.emit(str(exc))
        finally:
            stream.stop()

    def stop(self) -> None:
        """Ask the thread to end and wait for it (bounded)."""
        self.requestInterruption()
        if self._stream is not None:
            self._stream.stop()
        self.wait(5000)
