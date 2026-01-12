"""Session folder management for crawler sessions."""

import os
import glob
import shutil
import logging
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from mobile_crawler.infrastructure.run_repository import Run

logger = logging.getLogger(__name__)


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

    def get_session_path(self, run: "Run") -> Optional[str]:
        """Resolve the session folder path for a given run.
        
        Tries locations in order:
        1. screenshots/run_{id} (standard crawler output)
        2. Heuristic match in base_path (timestamped session folders)
        
        Args:
            run: The Run object
            
        Returns:
            Absolute path to the session folder if found, None otherwise
        """
        # 1. Check for standard crawler screenshot directory
        # This is where most runs store their data
        run_folder = os.path.join("screenshots", f"run_{run.id}")
        if os.path.exists(run_folder):
            return os.path.abspath(run_folder)
            
        # 2. Check for timestamped session folders in base_path (heuristics)
        if not os.path.exists(self.base_path):
            return None
            
        # Pattern to match folders for this device and package
        # format: {device_id}_{app_package}_{dd}_{mm}_{HH}_{MM}
        pattern = f"{run.device_id}_{run.app_package}_*"
        search_path = os.path.join(self.base_path, pattern)
        candidates = glob.glob(search_path)
        
        if not candidates:
            return None
            
        best_match = None
        min_diff = timedelta.max
        
        # We need to reconstruct a datetime from the folder name to compare
        # The folder format is "%d_%m_%H_%M" (missing year and seconds)
        # We'll use the run's year
        run_year = run.start_time.year
        
        for folder_path in candidates:
            folder_name = os.path.basename(folder_path)
            try:
                # Extract timestamp part
                # Assuming format: device_id_app_package_DD_MM_HH_MM
                parts = folder_name.split('_')
                if len(parts) < 4:
                    continue
                    
                # Last 4 parts are dd, mm, HH, MM
                time_parts = parts[-4:]
                day, month, hour, minute = map(int, time_parts)
                
                # Construct datetime
                folder_time = datetime(
                    year=run_year,
                    month=month,
                    day=day,
                    hour=hour,
                    minute=minute
                )
                
                # Calculate difference
                diff = abs(run.start_time - folder_time)
                
                # Filter out candidates that are too far apart (e.g. > 5 minutes)
                if diff < timedelta(minutes=5) and diff < min_diff:
                    min_diff = diff
                    best_match = folder_path
                    
            except (ValueError, IndexError):
                # Folder name didn't match format or parsing failed
                continue
                
        return os.path.abspath(best_match) if best_match else None
