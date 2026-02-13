"""Tests for the report CLI command."""

from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

import pytest

from mobile_crawler.cli.main import cli


class TestReportCommand:
    """Test the report command."""

    def test_report_command_help(self):
        """Test that report command shows help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['report', '--help'])
        assert result.exit_code == 0
        assert 'Generate a report for a crawl run' in result.output
        assert 'RUN_ID' in result.output
        assert '--output' in result.output
        assert '--format' in result.output

    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    @patch('mobile_crawler.domain.report_generator.ReportGenerator')
    def test_report_generate_pdf_success(self, mock_report_generator_cls, mock_db_manager_cls):
        """Test generating a PDF report successfully."""
        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager
        
        mock_report_generator = Mock()
        mock_report_generator.generate.return_value = '/path/to/report.pdf'
        mock_report_generator_cls.return_value = mock_report_generator

        runner = CliRunner()
        result = runner.invoke(cli, ['report', '123'])

        assert result.exit_code == 0
        assert 'PDF report generated: /path/to/report.pdf' in result.output
        mock_report_generator.generate.assert_called_once_with(123, None)

    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    @patch('mobile_crawler.domain.report_generator.ReportGenerator')
    def test_report_generate_pdf_with_output_path(self, mock_report_generator_cls, mock_db_manager_cls):
        """Test generating a PDF report with custom output path."""
        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager
        
        mock_report_generator = Mock()
        mock_report_generator.generate.return_value = '/custom/path/report.pdf'
        mock_report_generator_cls.return_value = mock_report_generator

        runner = CliRunner()
        result = runner.invoke(cli, ['report', '456', '--output', '/custom/path/report.pdf'])

        assert result.exit_code == 0
        assert 'PDF report generated: /custom/path/report.pdf' in result.output
        mock_report_generator.generate.assert_called_once_with(456, '/custom/path/report.pdf')

    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    @patch('mobile_crawler.domain.report_generator.ReportGenerator')
    def test_report_generate_html_fallback(self, mock_report_generator_cls, mock_db_manager_cls):
        """Test that HTML format falls back to PDF."""
        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager
        
        mock_report_generator = Mock()
        mock_report_generator.generate.return_value = '/path/to/report.pdf'
        mock_report_generator_cls.return_value = mock_report_generator

        runner = CliRunner()
        result = runner.invoke(cli, ['report', '789', '--format', 'html'])

        assert result.exit_code == 0
        assert 'HTML format not yet implemented' in result.output
        assert 'PDF report generated: /path/to/report.pdf' in result.output
        mock_report_generator.generate.assert_called_once_with(789, None)

    def test_report_invalid_run_id(self):
        """Test that invalid run ID is handled."""
        runner = CliRunner()
        result = runner.invoke(cli, ['report', 'invalid'])

        assert result.exit_code == 1
        assert 'Invalid run ID: invalid' in result.output

    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    @patch('mobile_crawler.domain.report_generator.ReportGenerator')
    def test_report_generation_error(self, mock_report_generator_cls, mock_db_manager_cls):
        """Test that report generation errors are handled."""
        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager
        
        mock_report_generator = Mock()
        mock_report_generator.generate.side_effect = Exception('Database connection failed')
        mock_report_generator_cls.return_value = mock_report_generator

        runner = CliRunner()
        result = runner.invoke(cli, ['report', '999'])

        assert result.exit_code == 1
        assert 'Error generating report: Database connection failed' in result.output

    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    @patch('mobile_crawler.domain.report_generator.ReportGenerator')
    def test_report_with_zero_run_id(self, mock_report_generator_cls, mock_db_manager_cls):
        """Test generating report for run ID 0."""
        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager
        
        mock_report_generator = Mock()
        mock_report_generator.generate.return_value = '/path/to/report.pdf'
        mock_report_generator_cls.return_value = mock_report_generator

        runner = CliRunner()
        result = runner.invoke(cli, ['report', '0'])

        assert result.exit_code == 0
        assert 'PDF report generated' in result.output
        mock_report_generator.generate.assert_called_once_with(0, None)

    @patch('mobile_crawler.infrastructure.database.DatabaseManager')
    @patch('mobile_crawler.domain.report_generator.ReportGenerator')
    def test_report_with_large_run_id(self, mock_report_generator_cls, mock_db_manager_cls):
        """Test generating report with large run ID."""
        mock_db_manager = Mock()
        mock_db_manager_cls.return_value = mock_db_manager
        
        mock_report_generator = Mock()
        mock_report_generator.generate.return_value = '/path/to/report.pdf'
        mock_report_generator_cls.return_value = mock_report_generator

        runner = CliRunner()
        result = runner.invoke(cli, ['report', '999999'])

        assert result.exit_code == 0
        assert 'PDF report generated' in result.output
        mock_report_generator.generate.assert_called_once_with(999999, None)
