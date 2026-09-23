"""Enumerates third-party packages installed on an Android device via ADB.

Qt-free so both the GUI's AppSelector and the CLI's `list apps` share one
enumeration. Display names come separately from AppMetadataResolver.
"""

import re
import subprocess

# Android package name: at least two dot-separated segments, each starting
# with a lowercase letter and containing only lowercase letters, digits and
# underscores.
_PACKAGE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


def is_valid_package_name(package: str) -> bool:
    """Return True if `package` looks like a valid Android package name."""
    return bool(_PACKAGE_NAME_PATTERN.match(package))


def parse_package_list(output: str) -> list[str]:
    """Parse `pm list packages` output into a sorted list of valid package names."""
    packages = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("package:"):
            package = line.replace("package:", "", 1).strip()
            if is_valid_package_name(package):
                packages.append(package)
    return sorted(packages)


def fetch_third_party_packages_output(device_id: str) -> str:
    """Run `pm list packages -3` on `device_id` and return its raw output.

    Raises:
        RuntimeError: if adb can't be run, times out or exits non-zero.
    """
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "pm", "list", "packages", "-3"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (subprocess.SubprocessError, OSError) as e:
        raise RuntimeError(f"ADB command failed: {e}") from e

    if result.returncode != 0:
        error_output = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(error_output or "ADB command failed")

    return result.stdout


def list_third_party_packages(device_id: str) -> list[str]:
    """Return the sorted third-party packages installed on `device_id`."""
    return parse_package_list(fetch_third_party_packages_output(device_id))


def is_package_installed(device_id: str, package: str) -> bool:
    """Return True if `package` (third-party or system) is installed on `device_id`.

    Raises:
        RuntimeError: if adb can't be run, times out or reports an error, so an unreachable
            device is never mistaken for a missing app.
    """
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "pm", "path", package],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError) as e:
        raise RuntimeError(f"ADB command failed: {e}") from e

    if any(line.strip().startswith("package:") for line in result.stdout.splitlines()):
        return True
    # `pm path` exits non-zero with no output for a missing package; anything on stderr is adb failing.
    if result.stderr.strip():
        raise RuntimeError(result.stderr.strip())
    return False
