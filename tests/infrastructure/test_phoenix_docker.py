from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from mobile_crawler.infrastructure import phoenix_docker
from mobile_crawler.infrastructure.phoenix_docker import (
    PHOENIX_IMAGE,
    PhoenixDockerService,
    is_local_phoenix_url,
    last_start_error,
)


@pytest.fixture(autouse=True)
def _clear_start_errors():
    phoenix_docker._last_start_errors.clear()
    yield
    phoenix_docker._last_start_errors.clear()


def test_image_is_pinned():
    assert PHOENIX_IMAGE == "arizephoenix/phoenix:version-20.3.0"


def test_port_is_taken_from_url_and_defaults_to_6006():
    assert PhoenixDockerService("http://localhost:7007/").port == 7007
    assert PhoenixDockerService("http://localhost").port == 6006


@pytest.mark.parametrize(
    ("url", "local"),
    [
        ("http://localhost:6006", True),
        ("http://127.0.0.1:6006", True),
        ("http://LOCALHOST:6006/", True),
        ("http://phoenix.example.com:6006", False),
        ("http://192.168.1.5:6006", False),
        ("", False),
    ],
)
def test_only_localhost_urls_are_managed(url, local):
    assert is_local_phoenix_url(url) is local


def test_reachable_requires_healthz_200():
    service = PhoenixDockerService("http://localhost:6006")
    with patch("requests.get", return_value=MagicMock(status_code=404)) as get:
        assert service.is_phoenix_reachable() is False
    assert get.call_args[0][0] == "http://localhost:6006/healthz"
    with patch("requests.get", return_value=MagicMock(status_code=200)):
        assert service.is_phoenix_reachable() is True
    with patch("requests.get", side_effect=requests.ConnectionError):
        assert service.is_phoenix_reachable() is False


def test_reuses_a_phoenix_that_already_answers():
    service = PhoenixDockerService()
    with patch.object(service, "is_phoenix_reachable", return_value=True), patch("subprocess.run") as run:
        ok, _ = service.ensure_running()
    assert ok and not service.started_by_gui
    run.assert_not_called()


def test_starts_nothing_when_the_port_is_held_by_something_else():
    service = PhoenixDockerService("http://localhost:6006")
    with (
        patch.object(service, "is_phoenix_reachable", return_value=False),
        patch.object(service, "port_in_use", return_value=True),
        patch.object(service, "is_running", return_value=False),
        patch("subprocess.run") as run,
    ):
        ok, message = service.ensure_running()
    assert not ok and "6006" in message and "not Phoenix" in message
    run.assert_not_called()
    assert last_start_error("http://localhost:6006") == message


def test_fails_without_docker():
    service = PhoenixDockerService()
    with (
        patch.object(service, "is_phoenix_reachable", return_value=False),
        patch.object(service, "port_in_use", return_value=False),
        patch.object(service, "docker_available", return_value=False),
    ):
        ok, message = service.ensure_running()
    assert not ok and "Docker" in message
    assert last_start_error("http://localhost:6006") == message


def test_starts_container_with_port_and_phoenix_dir_mount(tmp_path):
    phoenix_dir = tmp_path / ".phoenix"
    service = PhoenixDockerService("http://localhost:7007", phoenix_dir=phoenix_dir)
    phoenix_docker._last_start_errors[7007] = "old failure"
    reachable = iter([False, False, True])
    with (
        patch.object(service, "is_phoenix_reachable", side_effect=lambda: next(reachable)),
        patch.object(service, "port_in_use", return_value=False),
        patch.object(service, "docker_available", return_value=True),
        patch.object(service, "container_state", return_value="absent"),
        patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")) as run,
        patch("time.sleep"),
    ):
        ok, message = service.ensure_running()

    assert ok and service.started_by_gui, message
    assert phoenix_dir.is_dir()
    cmd = run.call_args[0][0]
    assert cmd[:3] == ["docker", "run", "-d"]
    assert cmd[-1] == PHOENIX_IMAGE
    assert cmd[cmd.index("-p") + 1] == "127.0.0.1:7007:6006"
    assert cmd[cmd.index("-v") + 1] == f"{phoenix_dir}:/mnt/data"
    assert "PHOENIX_WORKING_DIR=/mnt/data" in cmd
    assert last_start_error("http://localhost:7007") is None


def test_waits_for_its_own_container_that_holds_the_port_but_is_still_booting():
    service = PhoenixDockerService()
    reachable = iter([False, True])
    with (
        patch.object(service, "is_phoenix_reachable", side_effect=lambda: next(reachable)),
        patch.object(service, "port_in_use", return_value=True),
        patch.object(service, "container_state", return_value="running"),
        patch("subprocess.run") as run,
        patch("time.sleep"),
    ):
        ok, _ = service.ensure_running()
    assert ok
    run.assert_not_called()


def test_hung_own_container_times_out_with_a_docker_logs_hint():
    service = PhoenixDockerService()
    clock = iter(range(0, 1000, 10))
    with (
        patch.object(service, "is_phoenix_reachable", return_value=False),
        patch.object(service, "port_in_use", return_value=True),
        patch.object(service, "container_state", return_value="running"),
        patch("time.monotonic", side_effect=lambda: next(clock)),
        patch("time.sleep"),
    ):
        ok, message = service.ensure_running(timeout=30)
    assert not ok and "not Phoenix" not in message and "docker logs" in message


@pytest.mark.parametrize("state", ["stopped", "running"])
def test_replaces_an_old_container_that_does_not_hold_the_port(tmp_path, state):
    # "running" without holding the port: started earlier for another Phoenix URL.
    service = PhoenixDockerService(phoenix_dir=tmp_path)
    reachable = iter([False, True])
    with (
        patch.object(service, "is_phoenix_reachable", side_effect=lambda: next(reachable)),
        patch.object(service, "port_in_use", return_value=False),
        patch.object(service, "docker_available", return_value=True),
        patch.object(service, "container_state", return_value=state),
        patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")) as run,
        patch("time.sleep"),
    ):
        ok, _ = service.ensure_running()
    assert ok
    commands = [c[0][0] for c in run.call_args_list]
    assert commands[0] == ["docker", "rm", "-f", service.container_name]
    assert commands[1][:2] == ["docker", "run"]


def test_run_failure_is_reported(tmp_path):
    service = PhoenixDockerService(phoenix_dir=tmp_path)
    with (
        patch.object(service, "is_phoenix_reachable", return_value=False),
        patch.object(service, "port_in_use", return_value=False),
        patch.object(service, "docker_available", return_value=True),
        patch.object(service, "container_state", return_value="absent"),
        patch("subprocess.run", return_value=MagicMock(returncode=125, stdout="", stderr="pull access denied")),
    ):
        ok, message = service.ensure_running()
    assert not ok and "pull access denied" in message
    assert not service.started_by_gui
    assert last_start_error("http://localhost:6006") == message


def test_times_out_when_container_never_answers(tmp_path):
    service = PhoenixDockerService(phoenix_dir=tmp_path)
    clock = iter(range(0, 1000, 10))
    with (
        patch.object(service, "is_phoenix_reachable", return_value=False),
        patch.object(service, "port_in_use", return_value=False),
        patch.object(service, "docker_available", return_value=True),
        patch.object(service, "container_state", return_value="absent"),
        patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")),
        patch("time.monotonic", side_effect=lambda: next(clock)),
        patch("time.sleep"),
    ):
        ok, message = service.ensure_running(timeout=30)
    assert not ok and "30" in message


def test_default_phoenix_dir_is_home_dot_phoenix():
    assert PhoenixDockerService().phoenix_dir == Path.home() / ".phoenix"


def test_is_running_and_stop_use_the_container_name():
    service = PhoenixDockerService()
    with patch.object(service, "container_state", return_value="running"):
        assert service.is_running() is True
    with patch("subprocess.run") as run:
        service.stop()
    assert run.call_args[0][0] == ["docker", "stop", service.container_name]
