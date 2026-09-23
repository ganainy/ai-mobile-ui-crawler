"""Docker lifecycle management for the local Phoenix tracing server.

The third Managed Service, next to :mod:`mobsf_docker` and :mod:`omniparser_docker`.
Only a localhost ``phoenix_url`` is managed. A Phoenix that already answers
``/healthz`` (e.g. a leftover ``phoenix serve``) is reused, so two servers never
write to the same SQLite db, and a port held by something else is left alone.
``~/.phoenix`` is bind-mounted as Phoenix's working dir, so traces written by an
earlier ``phoenix serve`` stay readable.
"""

import logging
import shutil
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

# Pinned so traces in ~/.phoenix/phoenix.db are never migrated by a surprise upgrade.
PHOENIX_IMAGE = "arizephoenix/phoenix:version-20.3.0"
PHOENIX_CONTAINER_NAME = "mobile-crawler-phoenix"
PHOENIX_DEFAULT_URL = "http://localhost:6006"
PHOENIX_CONTAINER_PORT = 6006
PHOENIX_CONTAINER_DATA_DIR = "/mnt/data"
_LOCAL_HOSTS = ("localhost", "127.0.0.1")

# Why the last start attempt per port failed, so the Pre-run Warning can say so.
_last_start_errors: dict[int, str] = {}


def phoenix_tracing_url(config) -> str | None:
    """The ``phoenix_url`` traces go to, or None if Phoenix tracing is off.

    ``config`` is anything with ``get(key, default)``: a ConfigManager, or a dict of the GUI's
    unsaved Settings values.
    """
    if config.get("enable_tracing", False) is not True:
        return None
    if config.get("tracing_provider", "phoenix") != "phoenix":
        return None
    return config.get("phoenix_url", PHOENIX_DEFAULT_URL) or PHOENIX_DEFAULT_URL


def managed_phoenix_url(config) -> str | None:
    """The Phoenix URL the crawler starts itself: Phoenix tracing on and ``phoenix_url`` local."""
    url = phoenix_tracing_url(config)
    return url if url is not None and is_local_phoenix_url(url) else None


def is_local_phoenix_url(url: str) -> bool:
    """True if ``url`` points at this machine, i.e. a Phoenix the crawler may start itself."""
    host = urlparse(url or "").hostname
    return host is not None and host.lower() in _LOCAL_HOSTS


def last_start_error(url: str) -> str | None:
    """The message of the last failed start for ``url``'s port, None if it has not failed."""
    return _last_start_errors.get(_port_of(url))


def _port_of(url: str) -> int:
    return urlparse(url or "").port or PHOENIX_CONTAINER_PORT


class PhoenixDockerService:
    """Starts, monitors, and stops the Phoenix Docker container."""

    def __init__(
        self,
        url: str = PHOENIX_DEFAULT_URL,
        phoenix_dir: Path | None = None,
        container_name: str = PHOENIX_CONTAINER_NAME,
    ):
        self.url = url.rstrip("/")
        self.port = _port_of(self.url)
        self.phoenix_dir = phoenix_dir or Path.home() / ".phoenix"
        self.container_name = container_name
        self.started_by_gui = False

    def is_phoenix_reachable(self) -> bool:
        """Return True if a Phoenix server answers ``/healthz`` at the URL."""
        try:
            return requests.get(f"{self.url}/healthz", timeout=2).status_code == 200
        except requests.RequestException:
            return False

    def port_in_use(self) -> bool:
        """Return True if anything accepts TCP connections on the port."""
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=1):
                return True
        except OSError:
            return False

    def docker_available(self) -> bool:
        """Return True if the Docker CLI is present and the daemon responds."""
        if shutil.which("docker") is None:
            return False
        try:
            return subprocess.run(["docker", "info"], capture_output=True, timeout=15).returncode == 0
        except (OSError, subprocess.SubprocessError) as e:
            logger.warning("Docker daemon check failed: %s", e)
            return False

    def container_state(self) -> str:
        """Return the container state: 'running', 'stopped', or 'absent'."""
        try:
            result = self._docker(
                "ps", "-a", "--filter", f"name=^{self.container_name}$", "--format", "{{.Status}}", timeout=15
            )
        except (OSError, subprocess.SubprocessError) as e:
            logger.warning("Failed to inspect Phoenix container state: %s", e)
            return "absent"
        status = result.stdout.strip()
        if not status:
            return "absent"
        return "running" if status.lower().startswith("up") else "stopped"

    def ensure_running(self, timeout: int = 90) -> tuple[bool, str]:
        """Ensure a Phoenix server answers at the URL, starting the container if needed.

        Args:
            timeout: Maximum seconds to wait for ``/healthz`` after starting the container
                (the image pull itself is not counted).

        Returns:
            Tuple of (success, message).
        """
        if self.is_phoenix_reachable():
            _last_start_errors.pop(self.port, None)
            return True, "Phoenix is already reachable"

        if self.port_in_use():
            # Docker publishes the port before Phoenix answers: our own container may still be booting.
            if not self.is_running():
                return self._fail(
                    f"Port {self.port} is in use by something that is not Phoenix, so Phoenix was not started. "
                    "Free the port or change the Phoenix URL in Settings."
                )
        else:
            if not self.docker_available():
                return self._fail(
                    "Docker is not available. Install Docker Desktop and ensure the Docker daemon is running."
                )
            if self.container_state() != "absent":
                # Stopped, or running on another port (the Phoenix URL changed): replace it.
                try:
                    self._docker("rm", "-f", self.container_name, timeout=30)
                except (OSError, subprocess.SubprocessError) as e:
                    logger.warning("Failed to remove old Phoenix container: %s", e)
            started, message = self._run_container()
            if not started:
                return self._fail(message)

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.is_phoenix_reachable():
                _last_start_errors.pop(self.port, None)
                return True, "Phoenix is ready"
            time.sleep(1)
        return self._fail(
            f"The Phoenix container did not answer {self.url}/healthz within {timeout} seconds "
            f"(see `docker logs {self.container_name}`)"
        )

    def _run_container(self) -> tuple[bool, str]:
        try:
            self.phoenix_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return False, f"Failed to create {self.phoenix_dir}: {e}"
        self.started_by_gui = True
        try:
            # The first start pulls the image, which can take a few minutes.
            result = self._docker(
                "run",
                "-d",
                "--rm",
                "--name",
                self.container_name,
                "-p",
                f"127.0.0.1:{self.port}:{PHOENIX_CONTAINER_PORT}",
                "-v",
                f"{self.phoenix_dir}:{PHOENIX_CONTAINER_DATA_DIR}",
                "-e",
                f"PHOENIX_WORKING_DIR={PHOENIX_CONTAINER_DATA_DIR}",
                PHOENIX_IMAGE,
                timeout=900,
            )
        except (OSError, subprocess.SubprocessError) as e:
            self.started_by_gui = False
            return False, f"Failed to start Phoenix container: {e}"
        if result.returncode != 0:
            self.started_by_gui = False
            detail = (result.stderr or result.stdout).strip()[-300:]
            return False, f"Failed to start Phoenix container: {detail}"
        return True, "Phoenix container started"

    def _fail(self, message: str) -> tuple[bool, str]:
        _last_start_errors[self.port] = message
        return False, message

    def _docker(self, *args: str, timeout: int) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["docker", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )

    def is_running(self) -> bool:
        """Return True if this crawler's Phoenix container is running."""
        return self.container_state() == "running"

    def stop(self) -> None:
        """Stop the Phoenix container (started with ``--rm``, so it is removed too)."""
        try:
            self._docker("stop", self.container_name, timeout=60)
        except (OSError, subprocess.SubprocessError) as e:
            logger.warning("Failed to stop Phoenix container: %s", e)
