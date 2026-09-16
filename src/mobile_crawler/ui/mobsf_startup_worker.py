"""Background worker that ensures MobSF is running at GUI startup."""

from PySide6.QtCore import QThread, Signal

from mobile_crawler.infrastructure.mobsf_docker import MobSFDockerService


class MobSFStartupWorker(QThread):
    """Runs MobSF startup orchestration off the UI thread.

    Emits ``result(ok, message, started_by_gui)`` when finished. The message
    is a human-readable status line; ``started_by_gui`` reports whether this
    process launched the container.
    """

    result = Signal(bool, str, bool)

    def __init__(self, docker_service: MobSFDockerService, parent=None):
        super().__init__(parent)
        self._docker = docker_service

    def run(self):
        ok, message = self._docker.ensure_running()
        if not ok:
            self.result.emit(False, message, self._docker.started_by_gui)
            return

        api_key = self._docker.wait_for_api_key()
        if not api_key:
            self.result.emit(
                False,
                "MobSF is running but its REST API key could not be discovered from Docker logs.",
                self._docker.started_by_gui,
            )
            return

        self._docker.save_api_key(api_key)
        self.result.emit(True, "MobSF is ready", self._docker.started_by_gui)
