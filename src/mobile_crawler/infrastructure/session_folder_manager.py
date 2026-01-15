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

    def __init__(self, base_path: Optional[str] = None):
        """Initialize with base path for session folders.
        
        Args:
            base_path: Base directory for session folders. If None, uses app_data_dir/output_data.
        """
        if base_path is None:
            from mobile_crawler.config import get_app_data_dir
            base_path = str(get_app_data_dir() / "output_data")
            
        self.base_path = base_path

    def create_session_folder(self, run_id: int) -> str:
        """Create a new session folder with ID and timestamp.
        
        Args:
            run_id: Run ID
            
        Returns:
            Path to the created session folder
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"run_{run_id}_{timestamp}"
        session_path = os.path.join(self.base_path, folder_name)
        
        # Create main directory
        os.makedirs(session_path, exist_ok=True)
        
        # Create standard subdirectories
        # Separate folders for different artifact types: pcap, videos, logs, apks
        subdirs = ["screenshots", "reports", "pcap", "videos", "logs", "data", "apks"]
        for subdir in subdirs:
            os.makedirs(os.path.join(session_path, subdir), exist_ok=True)
        
        return os.path.abspath(session_path)

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
        1. run.session_path (explicitly stored in DB)
        2. screenshots/run_{id} (standard crawler output - legacy)
        3. Heuristic match in base_path (timestamped session folders - legacy)
        
        Args:
            run: The Run object
            
        Returns:
            Absolute path to the session folder if found, None otherwise
        """
        # 1. Check for explicitly stored path
        if hasattr(run, 'session_path') and run.session_path and os.path.exists(run.session_path):
            return os.path.abspath(run.session_path)

        # 2. Check for legacy crawler screenshot directory
        # This is where most runs store their data
        run_folder = os.path.join("screenshots", f"run_{run.id}")
        if os.path.exists(run_folder):
            return os.path.abspath(run_folder)
            
        # 3. Check for standard run_{id}_* folders in base_path
        if os.path.exists(self.base_path):
            standard_pattern = f"run_{run.id}_*"
            standard_search = os.path.join(self.base_path, standard_pattern)
            standard_candidates = glob.glob(standard_search)
            if standard_candidates:
                return os.path.abspath(standard_candidates[0])

        # 4. Check for timestamped session folders in base_path (legacy heuristics)
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

    def get_subfolder(self, run: "Run", subdir: str) -> str:
        """Get the absolute path to a subfolder within the session directory.
        
        Args:
            run: The Run object
            subdir: The subdirectory name (e.g., 'screenshots', 'reports', 'data')
            
        Returns:
            Absolute path to the subfolder
        """
        session_path = self.get_session_path(run)
        if not session_path:
            # Fallback for runs without session folders - create in current structure if missing?
            # For now, just return a path relative to current or base_path
            session_path = os.path.join(self.base_path, f"run_{run.id}")
            
        target_path = os.path.join(session_path, subdir)
        os.makedirs(target_path, exist_ok=True)
        return os.path.abspath(target_path)
