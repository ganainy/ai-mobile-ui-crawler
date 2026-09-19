"""Tests for the report CLI command."""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from mobile_crawler.cli.main import cli


def _invoke(args, generate_return="/path/to/report_run_1.html", generate_side_effect=None):
    """Run the report command with the database, config and generator mocked."""
    with (
        patch("mobile_crawler.infrastructure.database.DatabaseManager") as db_cls,
        patch("mobile_crawler.config.config_manager.ConfigManager") as config_cls,
        patch("mobile_crawler.domain.report_generator.ReportGenerator") as generator_cls,
    ):
        db_cls.return_value = Mock()
        config_cls.return_value = Mock()
        generator = Mock()
        generator.generate.return_value = generate_return
        generator.generate.side_effect = generate_side_effect
        generator_cls.return_value = generator
        result = CliRunner().invoke(cli, args)
    return result, generator, generator_cls


class TestReportCommand:
    """Test the report command."""

    def test_report_command_help(self):
        result = CliRunner().invoke(cli, ["report", "--help"])

        assert result.exit_code == 0
        assert "Generate a report for a crawl run" in result.output
        assert "RUN_ID" in result.output
        assert "--output" in result.output
        assert "--format" not in result.output  # the old PDF/HTML switch did nothing

    def test_report_generates_html_and_analysis_bundle_with_telemetry(self):
        result, generator, _ = _invoke(["report", "123"])

        assert result.exit_code == 0
        assert "Run report generated: /path/to/report_run_1.html" in result.output
        generator.generate.assert_called_once_with(123, None, fetch_telemetry=True)

    def test_report_with_custom_output_path(self):
        result, generator, _ = _invoke(
            ["report", "456", "--output", "/custom/path/report.html"],
            generate_return="/custom/path/report.html",
        )

        assert result.exit_code == 0
        assert "Run report generated: /custom/path/report.html" in result.output
        generator.generate.assert_called_once_with(456, "/custom/path/report.html", fetch_telemetry=True)

    def test_report_builds_generator_with_a_telemetry_client_factory(self):
        _, _, generator_cls = _invoke(["report", "1"])

        assert callable(generator_cls.call_args.kwargs["telemetry_client_factory"])

    def test_report_invalid_run_id(self):
        result = CliRunner().invoke(cli, ["report", "invalid"])

        assert result.exit_code == 1
        assert "Invalid run ID: invalid" in result.output

    def test_report_generation_error(self):
        result, _, _ = _invoke(["report", "999"], generate_side_effect=Exception("Database connection failed"))

        assert result.exit_code == 1
        assert "Error generating report: Database connection failed" in result.output

    def test_report_with_zero_run_id(self):
        result, generator, _ = _invoke(["report", "0"])

        assert result.exit_code == 0
        generator.generate.assert_called_once_with(0, None, fetch_telemetry=True)
