"""Tests for the CLI's Docker auto-start orchestration."""

from unittest.mock import Mock, patch

from mobile_crawler.infrastructure.docker_autostart import (
    ensure_mobsf_running_if_enabled,
    ensure_omniparser_running_if_enabled,
)


class TestEnsureMobsfRunningIfEnabled:
    def test_skips_when_not_enabled(self):
        config = Mock()
        config.get.return_value = False

        with patch("mobile_crawler.infrastructure.docker_autostart.MobSFDockerService") as service_cls:
            result = ensure_mobsf_running_if_enabled(config)

        assert result is None
        service_cls.assert_not_called()

    def test_prepares_container_when_enabled(self):
        config = Mock()
        config.get.return_value = True

        with patch("mobile_crawler.infrastructure.docker_autostart.MobSFDockerService") as service_cls:
            service_cls.return_value.prepare.return_value = (True, "MobSF is ready")
            result = ensure_mobsf_running_if_enabled(config)

        assert result == (True, "MobSF is ready")
        service_cls.return_value.prepare.assert_called_once()


class TestEnsureOmniparserRunningIfEnabled:
    def test_skips_when_accessibility_mode(self):
        config = Mock()
        config.get.side_effect = lambda key, default=None: {"ui_parser_mode": "accessibility"}.get(key, default)

        with patch("mobile_crawler.infrastructure.docker_autostart.OmniParserDockerService") as service_cls:
            result = ensure_omniparser_running_if_enabled(config)

        assert result is None
        service_cls.assert_not_called()

    def test_skips_when_backend_is_not_local(self):
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "ui_parser_mode": "omniparser",
            "omniparser_backend": "replicate",
        }.get(key, default)

        with patch("mobile_crawler.infrastructure.docker_autostart.OmniParserDockerService") as service_cls:
            result = ensure_omniparser_running_if_enabled(config)

        assert result is None
        service_cls.assert_not_called()

    def test_starts_local_backend(self):
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "ui_parser_mode": "omniparser",
            "omniparser_backend": "local",
            "omniparser_local_url": "http://localhost:9123",
        }.get(key, default)

        with patch("mobile_crawler.infrastructure.docker_autostart.OmniParserDockerService") as service_cls:
            service_cls.return_value.ensure_running.return_value = (True, "OmniParser is ready")
            result = ensure_omniparser_running_if_enabled(config)

        assert result == (True, "OmniParser is ready")
        service_cls.assert_called_once_with("http://localhost:9123")
