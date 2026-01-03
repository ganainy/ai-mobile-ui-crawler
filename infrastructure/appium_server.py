"""
Appium server management utilities.

Provides functionality to start and manage the Appium server in a separate terminal.
"""

import subprocess
import socket
import time
import sys
import os
from typing import Optional, Tuple


# Default Appium configuration
DEFAULT_APPIUM_PORT = 4723
APPIUM_STARTUP_TIMEOUT = 10  # seconds to wait for Appium to start


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is already in use.
    
    Args:
        port: Port number to check
        host: Host to check on (default localhost)
        
    Returns:
        True if port is in use, False otherwise
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False


def start_appium_server(
    port: int = DEFAULT_APPIUM_PORT,
    relaxed_security: bool = True,
    wait_for_startup: bool = True
) -> Tuple[bool, Optional[str]]:
    """Start Appium server in a separate terminal window.
    
    Args:
        port: Port to run Appium on (default 4723)
        relaxed_security: Whether to use --relaxed-security flag (default True)
        wait_for_startup: Whether to wait for Appium to start (default True)
        
    Returns:
        Tuple of (success: bool, message: str or None)
    """
    # Check if Appium is already running on the port
    if is_port_in_use(port):
        return True, f"Appium already running on port {port}"
    
    # Build the Appium command
    appium_cmd = f"npx appium -p {port}"
    if relaxed_security:
        appium_cmd += " --relaxed-security"
    
    try:
        if sys.platform == "win32":
            # Windows: Open new terminal with title
            # Use 'start' command with /MIN to minimize, or without to show
            terminal_title = f"Appium Server (Port {port})"
            # The command needs to keep the window open after Appium exits
            full_cmd = f'start "{terminal_title}" cmd /k "{appium_cmd}"'
            subprocess.Popen(full_cmd, shell=True)
        elif sys.platform == "darwin":
            # macOS: Open new Terminal.app window
            script = f'''
            tell application "Terminal"
                do script "{appium_cmd}"
                activate
            end tell
            '''
            subprocess.Popen(["osascript", "-e", script])
        else:
            # Linux: Try common terminal emulators
            terminals = [
                ["gnome-terminal", "--", "bash", "-c", f"{appium_cmd}; exec bash"],
                ["xterm", "-e", f"{appium_cmd}; bash"],
                ["konsole", "-e", f"{appium_cmd}; bash"],
            ]
            started = False
            for terminal_cmd in terminals:
                try:
                    subprocess.Popen(terminal_cmd)
                    started = True
                    break
                except FileNotFoundError:
                    continue
            if not started:
                return False, "No terminal emulator found (tried gnome-terminal, xterm, konsole)"
        
        # Wait for Appium to start if requested
        if wait_for_startup:
            start_time = time.time()
            while time.time() - start_time < APPIUM_STARTUP_TIMEOUT:
                if is_port_in_use(port):
                    return True, f"Appium server started on port {port}"
                time.sleep(0.5)
            
            # Check one more time
            if is_port_in_use(port):
                return True, f"Appium server started on port {port}"
            else:
                return False, f"Appium server did not start within {APPIUM_STARTUP_TIMEOUT}s (port {port} not responding)"
        
        return True, f"Appium server starting on port {port}"
        
    except Exception as e:
        return False, f"Failed to start Appium: {e}"


def ensure_appium_running(port: int = DEFAULT_APPIUM_PORT) -> bool:
    """Ensure Appium is running, starting it if necessary.
    
    Args:
        port: Port to check/start Appium on
        
    Returns:
        True if Appium is running, False otherwise
    """
    if is_port_in_use(port):
        return True
    
    success, message = start_appium_server(port=port)
    if message:
        print(f"[Appium] {message}")
    return success
