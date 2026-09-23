"""Tests for MobSFDockerService."""

from unittest.mock import Mock, patch

from mobile_crawler.infrastructure.mobsf_docker import MobSFDockerService
from mobile_crawler.infrastructure.mobsf_manager import extract_api_key_from_logs


class TestDockerAvailable:
    def test_false_when_cli_missing(self):
        service = MobSFDockerService()
        with patch(
            "mobile_crawler.infrastructure.mobsf_docker.shutil.which",
            return_value=None,
        ):
            assert service.docker_available() is False

    def test_false_when_daemon_not_running(self):
        service = MobSFDockerService()
        with patch(
            "mobile_crawler.infrastructure.mobsf_docker.shutil.which",
            return_value="docker",
        ):
            with patch(
                "mobile_crawler.infrastructure.mobsf_docker.subprocess.run",
                return_value=Mock(returncode=1),
            ):
                assert service.docker_available() is False

    def test_true_when_daemon_running(self):
        service = MobSFDockerService()
        with patch(
            "mobile_crawler.infrastructure.mobsf_docker.shutil.which",
            return_value="docker",
        ):
            with patch(
                "mobile_crawler.infrastructure.mobsf_docker.subprocess.run",
                return_value=Mock(returncode=0),
            ):
                assert service.docker_available() is True


class TestEnsureRunning:
    def test_already_reachable(self):
        service = MobSFDockerService()
        with patch.object(service, "is_mobsf_reachable", return_value=True):
            ok, message = service.ensure_running()
        assert ok is True
        assert service.started_by_gui is False

    def test_docker_missing(self):
        service = MobSFDockerService()
        with patch.object(service, "is_mobsf_reachable", return_value=False):
            with patch.object(service, "docker_available", return_value=False):
                ok, message = service.ensure_running()
        assert ok is False
        assert "Docker" in message

    def test_starts_absent_container(self):
        service = MobSFDockerService()
        with patch.object(
            service, "is_mobsf_reachable", side_effect=[False, True]
        ):
            with patch.object(service, "docker_available", return_value=True):
                with patch.object(service, "container_state", return_value="absent"):
                    with patch(
                        "mobile_crawler.infrastructure.mobsf_docker.subprocess.run"
                    ) as run:
                        ok, message = service.ensure_running()
        assert ok is True
        assert service.started_by_gui is True
        run.assert_called_once()
        args = run.call_args[0][0]
        assert args[0] == "docker"
        assert args[1] == "run"
        assert "-d" in args
        assert service.container_name in args

    def test_restarts_stopped_container(self):
        service = MobSFDockerService()
        with patch.object(
            service, "is_mobsf_reachable", side_effect=[False, True]
        ):
            with patch.object(service, "docker_available", return_value=True):
                with patch.object(service, "container_state", return_value="stopped"):
                    with patch(
                        "mobile_crawler.infrastructure.mobsf_docker.subprocess.run"
                    ) as run:
                        ok, _ = service.ensure_running()
        assert ok is True
        assert service.started_by_gui is True
        assert run.call_count >= 2
        assert run.call_args_list[0][0][0][1] == "rm"

    def test_timeout_when_never_reachable(self):
        service = MobSFDockerService()
        with patch.object(service, "is_mobsf_reachable", return_value=False):
            with patch.object(service, "docker_available", return_value=True):
                with patch.object(service, "container_state", return_value="absent"):
                    with patch(
                        "mobile_crawler.infrastructure.mobsf_docker.subprocess.run"
                    ):
                        with patch("mobile_crawler.infrastructure.mobsf_docker.time.sleep"):
                            ok, message = service.ensure_running(timeout=0.01)
        assert ok is False
        assert "reachable" in message


class TestApiKey:
    def test_extract_api_key(self):
        service = MobSFDockerService()
        logs = Mock(stdout="REST API Key: abcdef1234567890", stderr="")
        with patch(
            "mobile_crawler.infrastructure.mobsf_docker.subprocess.run",
            return_value=logs,
        ):
            assert service.extract_api_key() == "abcdef1234567890"

    def test_extract_api_key_strips_ansi(self):
        service = MobSFDockerService()
        logs = Mock(
            stdout="REST API Key: \x1b[1mabcdef1234567890\x1b[0m", stderr=""
        )
        with patch(
            "mobile_crawler.infrastructure.mobsf_docker.subprocess.run",
            return_value=logs,
        ):
            assert service.extract_api_key() == "abcdef1234567890"

    def test_wait_for_api_key_retries(self):
        service = MobSFDockerService()
        with patch.object(service, "extract_api_key", side_effect=["", "key123"]):
            with patch("mobile_crawler.infrastructure.mobsf_docker.time.sleep"):
                assert service.wait_for_api_key() == "key123"


class TestPrepare:
    def test_returns_failure_from_ensure_running(self):
        service = MobSFDockerService()
        with patch.object(service, "ensure_running", return_value=(False, "Docker is not available")):
            ok, message = service.prepare()
        assert ok is False
        assert message == "Docker is not available"

    def test_returns_failure_when_api_key_not_found(self):
        service = MobSFDockerService()
        with (
            patch.object(service, "ensure_running", return_value=(True, "MobSF is ready")),
            patch.object(service, "wait_for_api_key", return_value=""),
        ):
            ok, message = service.prepare()
        assert ok is False
        assert "API key" in message

    def test_saves_api_key_and_succeeds(self):
        service = MobSFDockerService()
        with (
            patch.object(service, "ensure_running", return_value=(True, "MobSF is ready")),
            patch.object(service, "wait_for_api_key", return_value="key123"),
            patch.object(service, "save_api_key") as save_api_key,
        ):
            ok, message = service.prepare()
        assert ok is True
        assert message == "MobSF is ready"
        save_api_key.assert_called_once_with("key123")


class TestStop:
    def test_stop_calls_docker_stop(self):
        service = MobSFDockerService()
        with patch(
            "mobile_crawler.infrastructure.mobsf_docker.subprocess.run"
        ) as run:
            service.stop()
        run.assert_called_once()
        assert run.call_args[0][0][0] == "docker"
        assert run.call_args[0][0][1] == "stop"


class TestExtractApiKeyFromLogs:
    def test_returns_empty_when_missing(self):
        assert extract_api_key_from_logs("no key here") == ""

    def test_extracts_plain_key(self):
        assert extract_api_key_from_logs("REST API Key: deadbeefcafe") == "deadbeefcafe"


class TestPortFromUrl:
    def test_default_port_is_mobsf_default_url_port(self):
        assert MobSFDockerService().port == 8000

    def test_port_derived_from_url(self):
        assert MobSFDockerService("http://localhost:9123/").port == 9123

    def test_published_port_maps_to_container_8000(self):
        service = MobSFDockerService("http://localhost:9123")
        with (
            patch.object(service, "is_mobsf_reachable", return_value=False),
            patch.object(service, "docker_available", return_value=True),
            patch.object(service, "container_state", return_value="absent"),
            patch("mobile_crawler.infrastructure.mobsf_docker.subprocess.run") as run,
        ):
            service.ensure_running(timeout=0)
        assert "9123:8000" in run.call_args[0][0]
