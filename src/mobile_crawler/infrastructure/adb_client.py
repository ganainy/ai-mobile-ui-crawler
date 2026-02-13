"""ADB client wrapper for async command execution."""

import asyncio
import logging
import subprocess
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class ADBClient:
    """Async ADB command execution wrapper.

    Provides async methods for executing ADB commands without blocking
    the main event loop. Handles timeouts, error detection, and output
    parsing.
    """

    def __init__(self, adb_executable: str = "adb", timeout: float = 30.0):
        """Initialize ADB client.

        Args:
            adb_executable: Path to ADB executable or 'adb' if in PATH
            timeout: Default timeout for commands in seconds
        """
        self.adb_executable = adb_executable
        self.default_timeout = timeout

    async def execute_async(
        self, command_list: List[str], suppress_stderr: bool = False, timeout: Optional[float] = None
    ) -> Tuple[str, int]:
        """Execute an ADB command asynchronously.

        Args:
            command_list: List of command arguments (without 'adb' prefix)
            suppress_stderr: If True, don't log stderr output
            timeout: Command timeout in seconds (uses default if None)

        Returns:
            Tuple of (combined_output, return_code)
            - combined_output: Combined stdout and stderr
            - return_code: Process return code (0 = success)
        """
        timeout = timeout or self.default_timeout
        full_command = [self.adb_executable] + command_list

        try:
            def run_sync_subprocess():
                return subprocess.run(
                    full_command,
                    capture_output=True,
                    text=True,
                    check=False,
                    encoding='utf-8',
                    errors='replace',
                    timeout=timeout,
                )

            result = await asyncio.to_thread(run_sync_subprocess)

            # Combine stdout and stderr
            combined_output = result.stdout.strip()
            if result.stderr:
                if not suppress_stderr:
                    logger.debug(f"ADB stderr: {result.stderr.strip()}")
                combined_output += "\n" + result.stderr.strip() if combined_output else result.stderr.strip()

            return combined_output, result.returncode

        except subprocess.TimeoutExpired:
            logger.error(f"ADB command timed out after {timeout}s: {' '.join(full_command)}")
            return f"Command timed out after {timeout}s", -1
        except FileNotFoundError:
            logger.error(f"ADB executable not found: {self.adb_executable}")
            return "ADB_NOT_FOUND", -1
        except Exception as e:
            logger.error(f"Exception executing ADB command: {e}", exc_info=True)
            return str(e), -1

    def execute(self, command: str, timeout: Optional[float] = None) -> Optional[str]:
        """Execute an ADB command synchronously (for backward compatibility).

        Args:
            command: ADB command string (without 'adb' prefix)
            timeout: Command timeout in seconds

        Returns:
            Command output as string, or None if failed
        """
        command_list = command.split()
        output, return_code = asyncio.run(self.execute_async(command_list, timeout=timeout))
        return output if return_code == 0 else None
