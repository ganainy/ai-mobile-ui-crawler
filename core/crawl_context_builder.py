import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class CrawlContextBuilder:
    """
    Gathers and processes context for the crawler (action history, visited screens, etc.).
    """
    
    def __init__(self, db_manager, config):
        self.db_manager = db_manager
        self.config = config

    def get_crawl_context(self, current_run_id: int, from_screen_id: Optional[int]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Collect structured action history and context from database.
        
        Returns:
            (action_history, visited_screens, current_screen_actions)
        """
        action_history = []
        visited_screens = []
        current_screen_actions = []
        
        if not self.db_manager or not current_run_id:
            return action_history, visited_screens, current_screen_actions

        try:
            # Get recent steps with details (last 20 steps)
            action_history = self.db_manager.get_recent_steps_with_details(
                current_run_id, limit=20
            )
            
            # Get visited screens summary (filter out system dialogs)
            all_visited_screens = self.db_manager.get_visited_screens_summary(
                current_run_id
            )
            
            visited_screens = self._filter_visited_screens(all_visited_screens)
            
            # Get actions already tried on current screen (if we know the screen ID)
            if from_screen_id is not None:
                current_screen_actions = self.db_manager.get_actions_for_screen_with_details(
                    from_screen_id, run_id=current_run_id
                )
        except Exception as e:
            logger.warning(f"Error collecting action history from database: {e}", exc_info=True)
            
        return action_history, visited_screens, current_screen_actions

    def _filter_visited_screens(self, all_visited_screens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out system dialogs and file pickers from visited screens."""
        visited_screens = []
        target_package = self.config.get('APP_PACKAGE', '')
        
        # Late import to avoid circular dependency
        try:
            from config.package_constants import PackageConstants
        except ImportError:
            # Fallback if PackageConstants is not available directly
            class PackageConstants:
                @staticmethod
                def is_system_package(pkg): return pkg in ['com.android', 'com.google.android']
        
        for screen in all_visited_screens:
            activity = screen.get('activity_name', '')
            # Skip system dialogs and file pickers
            if activity and (
                'documentsui' in activity.lower() or
                'picker' in activity.lower() or
                PackageConstants.is_system_package(activity.split('.')[0] if '.' in activity else activity)
            ):
                continue
            
            # Only include screens from target app or explicitly allowed packages
            if activity and target_package:
                activity_package = activity.split('.')[0] if '.' in activity else ''
                if activity_package and activity_package != target_package:
                    # Check if it's in allowed external packages
                    allowed_packages = self.config.get('ALLOWED_EXTERNAL_PACKAGES', [])
                    if isinstance(allowed_packages, list) and activity_package not in allowed_packages:
                        continue
            visited_screens.append(screen)
            
        return visited_screens
