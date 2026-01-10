"""Session folder management for crawler sessions."""

import os
import shutil
from datetime import datetime


class SessionFolderManager:
    """Manages creation and deletion of session folders with subdirectories."""

    def __init__(self, base_path: str = "output_data"):
        """Initialize with base path for session folders.
        
        Args:
            base_path: Base directory for session folders
        """
        self.base_path = base_path

    def create_session_folder(self, device_id: str, app_package: str) -> str:
        """Create a new session folder with timestamp and subdirectories.
        
        Args:
            device_id: Device identifier
            app_package: App package name
            
        Returns:
            Path to the created session folder
        """
        timestamp = datetime.now().strftime("%d_%m_%H_%M")
        folder_name = f"{device_id}_{app_package}_{timestamp}"
        session_path = os.path.join(self.base_path, folder_name)
        
        # Create main directory
        os.makedirs(session_path, exist_ok=True)
        
        # Create subdirectories
        subdirs = ["screenshots", "logs", "video", "data"]
        for subdir in subdirs:
            os.makedirs(os.path.join(session_path, subdir), exist_ok=True)
        
        return session_path

    def delete_session_folder(self, session_path: str):
        """Delete a session folder and all its contents.
        
        Args:
            session_path: Path to the session folder to delete
        """
        if os.path.exists(session_path):
            shutil.rmtree(session_path)