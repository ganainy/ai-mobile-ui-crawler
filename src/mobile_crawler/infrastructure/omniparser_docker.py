"""Docker lifecycle management for the local OmniParser server.

Mirrors :mod:`mobile_crawler.infrastructure.mobsf_docker`, but drives the
compose stack in ``docker/omniparser`` and health-checks over HTTP rather than
a bare TCP connect, so an unrelated service on the same port (e.g. MobSF) is
not mistaken for OmniParser.
"""

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from mobile_crawler.infrastructure.mobsf_docker import MobSFDockerService

logger = logging.getLogger(__name__)

OMNIPARSER_DEFAULT_URL = "http://localhost:8001"
OMNIPARSER_COMPOSE_FILE = Path(__file__).resolve().parents[3] / "docker" / "omniparser" / "docker-compose.yml"


class OmniParserDockerService:
    """Starts, monitors, and stops the OmniParser Docker compose stack."""

    def __init__(self, url: str = OMNIPARSER_DEFAULT_URL, compose_file: Path = OMNIPARSER_COMPOSE_FILE):
        self.url = url.rstrip("/")
        self.compose_file = compose_file
        self.port = urlparse(self.url).port or 8001
        self.started_by_gui = False
        # Human-readable progress line, polled by the UI while startup runs.
        self.status = "Not started"

    def is_omniparser_reachable(self) -> bool:
        """Return True if an OmniParser server answers ``/probe/`` at the URL."""
        try:
            return requests.get(f"{self.url}/probe/", timeout=2).status_code == 200
        except requests.RequestException:
            return False

    def _compose(self, *args: str, timeout: int) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["docker", "compose", "-f", str(self.compose_file), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env={**os.environ, "OMNIPARSER_PORT": str(self.port)},
        )

    def ensure_running(self, timeout: int = 300) -> tuple[bool, str]:
        """Ensure OmniParser is running and answering health probes.

        Args:
            timeout: Maximum seconds to wait for the server after starting it
                (model loading can take a while on first start).

        Returns:
            Tuple of (success, message).
        """
        self.status = "Checking whether the server is already running..."
        if self.is_omniparser_reachable():
            self.status = "Ready"
            return True, "OmniParser is already reachable"

        self.status = "Checking Docker..."
        if shutil.which("docker") is None or not MobSFDockerService().docker_available():
            return False, (
                "Docker is not available. Install Docker Desktop and ensure the "
                "Docker daemon is running, then restart the GUI."
            )

        if not self.compose_file.is_file():
            return False, f"OmniParser compose file not found: {self.compose_file}"

        self.started_by_gui = True
        self.status = "Starting the container (the first run builds the image and downloads model weights)..."
        try:
            # First run builds the image and downloads weights, which is slow.
            result = self._compose("up", "-d", timeout=1800)
        except (OSError, subprocess.SubprocessError) as e:
            self.started_by_gui = False
            return False, f"Failed to start OmniParser container: {e}"
        if result.returncode != 0:
            self.started_by_gui = False
            detail = (result.stderr or result.stdout).strip()[-300:]
            return False, f"Failed to start OmniParser container: {detail}"

        started = time.monotonic()
        deadline = started + timeout
        while time.monotonic() < deadline:
            self.status = (
                f"Container started; loading models, waiting for {self.url}/probe/ "
                f"({int(time.monotonic() - started)}s / {timeout}s)..."
            )
            if self.is_omniparser_reachable():
                self.status = "Ready"
                return True, "OmniParser is ready"
            time.sleep(2)

        return False, f"OmniParser did not answer {self.url}/probe/ within {timeout} seconds"

    def is_running(self) -> bool:
        """Return True if the compose stack has a running container."""
        try:
            result = self._compose("ps", "--status", "running", "-q", timeout=30)
        except (OSError, subprocess.SubprocessError):
            return False
        return bool(result.stdout.strip())

    def stop(self) -> None:
        """Stop the OmniParser compose stack (keeps the container and image)."""
        try:
            self._compose("stop", timeout=60)
        except (OSError, subprocess.SubprocessError) as e:
            logger.warning("Failed to stop OmniParser container: %s", e)
