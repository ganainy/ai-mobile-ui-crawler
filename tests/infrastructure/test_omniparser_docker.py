from unittest.mock import MagicMock, patch

import requests

from mobile_crawler.infrastructure.omniparser_docker import OmniParserDockerService


def test_port_is_taken_from_url():
    assert OmniParserDockerService("http://localhost:9123/").port == 9123


def test_reachable_requires_probe_200():
    service = OmniParserDockerService()
    with patch("requests.get", return_value=MagicMock(status_code=404)):
        assert service.is_omniparser_reachable() is False
    with patch("requests.get", return_value=MagicMock(status_code=200)):
        assert service.is_omniparser_reachable() is True
    with patch("requests.get", side_effect=requests.ConnectionError):
        assert service.is_omniparser_reachable() is False


def test_ensure_running_skips_docker_when_already_reachable():
    service = OmniParserDockerService()
    with patch.object(service, "is_omniparser_reachable", return_value=True), patch("subprocess.run") as run:
        ok, _ = service.ensure_running()
    assert ok and not service.started_by_gui
    run.assert_not_called()


def test_ensure_running_starts_compose_with_port_env():
    service = OmniParserDockerService("http://localhost:8123")
    reachable = iter([False, True])
    with (
        patch.object(service, "is_omniparser_reachable", side_effect=lambda: next(reachable)),
        patch("shutil.which", return_value="docker"),
        patch(
            "mobile_crawler.infrastructure.omniparser_docker.MobSFDockerService.docker_available",
            return_value=True,
        ),
        patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")) as run,
        patch("time.sleep"),
    ):
        ok, message = service.ensure_running()
    assert ok and service.started_by_gui, message
    args, kwargs = run.call_args
    assert args[0][:2] == ["docker", "compose"] and args[0][-2:] == ["up", "-d"]
    assert kwargs["env"]["OMNIPARSER_PORT"] == "8123"
