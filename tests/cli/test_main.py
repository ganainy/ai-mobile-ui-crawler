"""Tests for CLI main module."""

from click.testing import CliRunner
from mobile_crawler.cli.main import cli


class TestCliMain:
    """Tests for the main CLI entry point."""

    def test_cli_help(self):
        """Test that CLI shows help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Mobile Crawler" in result.output
        assert "AI-powered Android exploration tool" in result.output
        assert "--version" in result.output

    def test_cli_version(self):
        """Test that CLI shows version."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "mobile-crawler, version" in result.output

    def test_cli_no_command(self):
        """Test that CLI shows help when no command given."""
        runner = CliRunner()
        result = runner.invoke(cli, [])

        assert result.exit_code == 0
        assert "Mobile Crawler" in result.output