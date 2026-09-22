"""Tests for `list apps --device ID`."""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from mobile_crawler.cli.main import cli
from mobile_crawler.infrastructure.app_metadata_resolver import AppMetadata

PACKAGES = 'mobile_crawler.infrastructure.installed_apps.list_third_party_packages'
RESOLVER = 'mobile_crawler.infrastructure.app_metadata_resolver.AppMetadataResolver'


def _resolver_with_labels(labels):
    resolver = Mock()
    resolver.resolve.side_effect = lambda device_id, package: AppMetadata(
        package=package, label=labels.get(package, package), icon_path=None,
        source='local' if package in labels else 'unresolved',
    )
    return resolver


class TestListApps:
    def test_help_mentions_apps_and_device(self):
        result = CliRunner().invoke(cli, ['list', '--help'])
        assert result.exit_code == 0
        assert 'apps' in result.output
        assert '--device' in result.output

    def test_requires_device(self):
        result = CliRunner().invoke(cli, ['list', 'apps'])
        assert result.exit_code != 0
        assert '--device' in result.output

    def test_device_rejected_for_other_targets(self):
        result = CliRunner().invoke(cli, ['list', 'runs', '--device', 'd1'])
        assert result.exit_code != 0
        assert "only apply to 'list apps'" in result.output

    @patch(RESOLVER)
    @patch(PACKAGES)
    def test_table_lists_packages_with_names(self, mock_packages, mock_resolver_cls):
        mock_packages.return_value = ['com.alpha.app', 'com.beta.app']
        mock_resolver_cls.return_value = _resolver_with_labels({'com.alpha.app': 'Alpha'})

        result = CliRunner().invoke(cli, ['list', 'apps', '--device', 'emulator-5554'])

        assert result.exit_code == 0, result.output
        mock_packages.assert_called_once_with('emulator-5554')
        assert 'com.alpha.app' in result.output
        assert 'Alpha' in result.output
        assert 'com.beta.app' in result.output

    @patch(RESOLVER)
    @patch(PACKAGES)
    def test_json_format(self, mock_packages, mock_resolver_cls):
        mock_packages.return_value = ['com.alpha.app', 'com.beta.app']
        mock_resolver_cls.return_value = _resolver_with_labels({'com.alpha.app': 'Alpha'})

        result = CliRunner().invoke(cli, ['list', 'apps', '--device', 'd1', '--format', 'json'])

        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout) == [
            {'package': 'com.alpha.app', 'name': 'Alpha'},
            {'package': 'com.beta.app', 'name': None},
        ]

    @patch(RESOLVER)
    @patch(PACKAGES)
    def test_lists_all_apps_by_default(self, mock_packages, mock_resolver_cls):
        packages = [f'com.app{i}.x' for i in range(15)]
        mock_packages.return_value = packages
        mock_resolver_cls.return_value = _resolver_with_labels({})

        result = CliRunner().invoke(cli, ['list', 'apps', '--device', 'd1', '--format', 'json'])

        assert len(json.loads(result.stdout)) == 15

    @patch(RESOLVER)
    @patch(PACKAGES)
    def test_limit_applies_before_resolving(self, mock_packages, mock_resolver_cls):
        mock_packages.return_value = ['com.a.x', 'com.b.x', 'com.c.x']
        resolver = _resolver_with_labels({})
        mock_resolver_cls.return_value = resolver

        result = CliRunner().invoke(cli, ['list', 'apps', '--device', 'd1', '-n', '2', '--format', 'json'])

        assert [a['package'] for a in json.loads(result.stdout)] == ['com.a.x', 'com.b.x']
        assert resolver.resolve.call_count == 2

    @patch(RESOLVER)
    @patch(PACKAGES)
    def test_no_names_skips_resolution(self, mock_packages, mock_resolver_cls):
        mock_packages.return_value = ['com.alpha.app']

        result = CliRunner().invoke(cli, ['list', 'apps', '--device', 'd1', '--no-names', '--format', 'json'])

        assert result.exit_code == 0, result.output
        mock_resolver_cls.assert_not_called()
        assert json.loads(result.stdout) == [{'package': 'com.alpha.app', 'name': None}]

    @patch(RESOLVER)
    @patch(PACKAGES)
    def test_resolver_failure_falls_back_to_no_name(self, mock_packages, mock_resolver_cls):
        mock_packages.return_value = ['com.alpha.app']
        mock_resolver_cls.return_value.resolve.side_effect = RuntimeError('boom')

        result = CliRunner().invoke(cli, ['list', 'apps', '--device', 'd1', '--format', 'json'])

        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout) == [{'package': 'com.alpha.app', 'name': None}]

    @patch(RESOLVER)
    @patch(PACKAGES)
    def test_empty(self, mock_packages, mock_resolver_cls):
        mock_packages.return_value = []

        result = CliRunner().invoke(cli, ['list', 'apps', '--device', 'd1'])

        assert result.exit_code == 0
        assert 'No third-party apps found' in result.output

    @patch(PACKAGES)
    def test_adb_error_aborts(self, mock_packages):
        mock_packages.side_effect = RuntimeError("error: device 'd1' not found")

        result = CliRunner().invoke(cli, ['list', 'apps', '--device', 'd1'])

        assert result.exit_code != 0
        assert "device 'd1' not found" in result.output
