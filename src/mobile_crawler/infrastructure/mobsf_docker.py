"""Docker lifecycle management for the MobSF static-analysis server.

Ports the container orchestration that previously lived in
``scripts/start.ps1`` into Python so the GUI can start, wait for, and stop
MobSF on its own.
"""

import logging
import shutil
import socket
import subprocess
import time
from urllib.parse import urlparse

from mobile_crawler.config.defaults import MOBSF_DEFAULT_URL
from mobile_crawler.infrastructure.mobsf_manager import (
    MOBSF_CONTAINER_NAME,
    extract_api_key_from_logs,
    save_api_key_file,
)

logger = logging.getLogger(__name__)

MOBSF_IMAGE = "opensecurity/mobile-security-framework-mobsf"
# Port MobSF listens on inside the container.
MOBSF_CONTAINER_PORT = 8000


class MobSFDockerService:
    """Starts, monitors, and stops the MobSF Docker container.

    The container is launched detached so it survives GUI restarts. The
    ``started_by_gui`` flag records whether this process launched the
    container, which the UI uses to decide whether to offer to stop it.
    The host and port come from the MobSF API URL (the default when it is
    empty), so the container is published and probed where the API calls go.
    """

    def __init__(
        self,
        url: str | None = None,
        image: str = MOBSF_IMAGE,
        container_name: str = MOBSF_CONTAINER_NAME,
    ):
        self.url = (url or MOBSF_DEFAULT_URL).rstrip("/")
        self.image = image
        self.container_name = container_name
        parsed = urlparse(self.url)
        self.host = parsed.hostname or urlparse(MOBSF_DEFAULT_URL).hostname
        self.port = parsed.port or urlparse(MOBSF_DEFAULT_URL).port
        self.started_by_gui = False

    def docker_available(self) -> bool:
        """Return True if the Docker CLI is present and the daemon responds."""
        if shutil.which("docker") is None:
            return False
        try:
            result = subprocess.run(["docker", "info"], capture_output=True, timeout=15)
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError) as e:
            logger.warning("Docker daemon check failed: %s", e)
            return False

    def is_mobsf_reachable(self) -> bool:
        """Return True if the MobSF server accepts connections at the URL's host and port."""
        try:
            with socket.create_connection((self.host, self.port), timeout=2):
                return True
        except OSError:
            return False

    def container_state(self) -> str:
        """Return the MobSF container state: 'running', 'stopped', or 'absent'."""
        try:
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "-a",
                    "--filter",
                    f"name=^{self.container_name}$",
                    "--format",
                    "{{.Status}}",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError) as e:
            logger.warning("Failed to inspect MobSF container state: %s", e)
            return "absent"

        status = result.stdout.strip()
        if not status:
            return "absent"
        if status.lower().startswith("up"):
            return "running"
        return "stopped"

    def ensure_running(self, timeout: int = 120) -> tuple[bool, str]:
        """Ensure the MobSF container is running and reachable.

        Args:
            timeout: Maximum seconds to wait for the server to become reachable.

        Returns:
            Tuple of (success, message).
        """
        if self.is_mobsf_reachable():
            return True, "MobSF is already reachable"

        if not self.docker_available():
            return False, (
                "Docker is not available. Install Docker Desktop and ensure the "
                "Docker daemon is running, then restart the GUI."
            )

        state = self.container_state()
        if state == "absent":
            self.started_by_gui = True
            try:
                subprocess.run(
                    [
                        "docker",
                        "run",
                        "-d",
                        "--name",
                        self.container_name,
                        "--rm",
                        "-p",
                        f"{self.port}:{MOBSF_CONTAINER_PORT}",
                        self.image,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
            except (OSError, subprocess.SubprocessError) as e:
                message = str(e)
                if hasattr(e, "stderr") and e.stderr:
                    message = f"{message} {e.stderr.strip()[:200]}"
                self.started_by_gui = False
                return False, f"Failed to start MobSF container: {message}"
        elif state == "stopped":
            self.started_by_gui = True
            subprocess.run(
                ["docker", "rm", self.container_name],
                capture_output=True,
                timeout=30,
            )
            try:
                subprocess.run(
                    [
                        "docker",
                        "run",
                        "-d",
                        "--name",
                        self.container_name,
                        "--rm",
                        "-p",
                        f"{self.port}:{MOBSF_CONTAINER_PORT}",
                        self.image,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
            except (OSError, subprocess.SubprocessError) as e:
                self.started_by_gui = False
                return False, f"Failed to restart MobSF container: {e}"
        # else: running but not yet reachable; fall through and wait.

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.is_mobsf_reachable():
                return True, "MobSF is ready"
            time.sleep(1)

        return False, f"MobSF did not become reachable within {timeout} seconds"

    def extract_api_key(self) -> str:
        """Extract the MobSF REST API key from the container logs."""
        try:
            result = subprocess.run(
                ["docker", "logs", self.container_name],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as e:
            logger.warning("Failed to read MobSF Docker logs: %s", e)
            return ""

        return extract_api_key_from_logs(f"{result.stdout}\n{result.stderr}")

    def wait_for_api_key(self, timeout: int = 90) -> str:
        """Poll the container logs until the API key appears or timeout elapses."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            key = self.extract_api_key()
            if key:
                return key
            time.sleep(2)
        return ""

    def save_api_key(self, api_key: str) -> None:
        """Cache a discovered API key to .mobsf_api_key."""
        save_api_key_file(api_key)

    def prepare(self, timeout: int = 120) -> tuple[bool, str]:
        """Ensure MobSF is running and its REST API key is discovered and cached.

        Combines :meth:`ensure_running`, :meth:`wait_for_api_key`, and
        :meth:`save_api_key` into the full startup sequence a caller needs
        before MobSF can be used for analysis.
        """
        ok, message = self.ensure_running(timeout=timeout)
        if not ok:
            return False, message

        api_key = self.wait_for_api_key()
        if not api_key:
            return False, "MobSF is running but its REST API key could not be discovered from Docker logs."

        self.save_api_key(api_key)
        return True, "MobSF is ready"

    def is_running(self) -> bool:
        """Return True if the MobSF container is currently running."""
        return self.container_state() == "running"

    def stop(self) -> None:
        """Stop the MobSF container gracefully."""
        try:
            subprocess.run(
                ["docker", "stop", self.container_name],
                capture_output=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as e:
            logger.warning("Failed to stop MobSF container: %s", e)
