"""Unit tests for ADBClient async execution."""

import asyncio
import subprocess
from unittest.mock import patch, MagicMock

import pytest

from mobile_crawler.infrastructure.adb_client import ADBClient


class TestADBClient:
    @pytest.fixture
    def client(self):
        return ADBClient()

    @patch("subprocess.run")
    def test_execute_async_success(self, mock_run, client):
        mock_run.return_value = MagicMock(returncode=0, stdout="device_list", stderr="")

        async def _run():
            output, code = await client.execute_async(["devices"])
            assert code == 0
            assert "device_list" in output

        asyncio.run(_run())

    @patch("subprocess.run")
    def test_execute_async_failure(self, mock_run, client):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        async def _run():
            output, code = await client.execute_async(["devices"])
            assert code == 1
            assert "error" in output

        asyncio.run(_run())

    @patch("subprocess.run")
    def test_benign_activity_delivered_stderr_not_logged(self, mock_run, client, caplog):
        benign = "Activity not started, intent has been delivered to currently running top-most instance."
        mock_run.return_value = MagicMock(returncode=0, stdout="Starting: Intent", stderr=benign)

        async def _run():
            with caplog.at_level("DEBUG"):
                output, code = await client.execute_async(["shell", "am", "start"])
            assert code == 0
            assert benign in output
            assert "ADB stderr" not in caplog.text
            assert benign not in caplog.text

        asyncio.run(_run())

    @patch("subprocess.run")
    def test_non_benign_stderr_still_logged_and_combined(self, mock_run, client, caplog):
        mock_run.return_value = MagicMock(returncode=0, stdout="stdout", stderr="real warning")

        async def _run():
            with caplog.at_level("DEBUG"):
                output, code = await client.execute_async(["devices"])
            assert code == 0
            assert "stdout" in output
            assert "real warning" in output
            assert "ADB stderr: real warning" in caplog.text

        asyncio.run(_run())

    @patch("subprocess.run")
    def test_execute_async_timeout(self, mock_run, client):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["adb"], timeout=30)

        async def _run():
            output, code = await client.execute_async(["shell", "sleep", "60"])
            assert code == -1
            assert "timed out" in output.lower()

        asyncio.run(_run())

    @patch("subprocess.run")
    def test_execute_async_not_found(self, mock_run, client):
        mock_run.side_effect = FileNotFoundError()

        async def _run():
            output, code = await client.execute_async(["devices"])
            assert code == -1
            assert "ADB_NOT_FOUND" in output

        asyncio.run(_run())
