"""Background worker that ensures the local OmniParser server is running at GUI startup."""

from PySide6.QtCore import QThread, Signal

from mobile_crawler.infrastructure.omniparser_docker import OmniParserDockerService


class OmniParserStartupWorker(QThread):
    """Runs OmniParser startup orchestration off the UI thread.

    Emits ``result(ok, message, started_by_gui)`` when finished.
    """

    result = Signal(bool, str, bool)

    def __init__(self, docker_service: OmniParserDockerService, parent=None):
        super().__init__(parent)
        self._docker = docker_service

    def run(self):
        ok, message = self._docker.ensure_running()
        self.result.emit(ok, message, self._docker.started_by_gui)
