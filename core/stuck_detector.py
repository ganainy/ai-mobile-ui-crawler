import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class StuckDetector:
    """
    Detects if the crawler is stuck in a loop (same screen, multiple actions, no navigation).
    """
    
    def __init__(self, config):
        self.config = config

    def check_if_stuck(self, 
                       from_screen_id: Optional[int], 
                       current_screen_visit_count: int,
                       action_history: List[Dict[str, Any]], 
                       current_screen_actions: List[Dict[str, Any]]) -> tuple[bool, str]:
        """
        Detect if stuck in a loop based on visit counts and action history.
        
        Returns:
            (is_stuck, stuck_reason)
        """
        # First, check if the last action successfully navigated to a different screen
        # If it did, we're NOT stuck (false positive prevention)
        last_action_navigated_away = False
        if action_history and len(action_history) > 0:
            last_action = action_history[-1]
            last_from_screen = last_action.get('from_screen_id')
            last_to_screen = last_action.get('to_screen_id')
            last_success = last_action.get('execution_success', False)
            
            # If last action successfully navigated to a different screen, we're not stuck
            if last_success and last_to_screen is not None and last_from_screen is not None:
                if last_to_screen != last_from_screen:
                    last_action_navigated_away = True
                    logger.debug(f"Last action navigated from Screen #{last_from_screen} to Screen #{last_to_screen} - not stuck")
        
        # Only check for stuck if we didn't just navigate away AND we're on a known screen
        if not last_action_navigated_away and from_screen_id is not None and current_screen_actions:
            # Count successful actions that stayed on same screen (exclude actions that navigated away)
            same_screen_actions = [a for a in current_screen_actions 
                                 if a.get('execution_success') and 
                                 (a.get('to_screen_id') == from_screen_id or a.get('to_screen_id') is None)]
            
            # Consider stuck if:
            # 1. High visit count (>5) on same screen
            # 2. Multiple successful actions that didn't navigate away (>=3)
            # 3. All recent actions (last 5) stayed on same screen
            if current_screen_visit_count > 5:
                reason = f"High visit count ({current_screen_visit_count}) on same screen"
                return True, reason
            elif len(same_screen_actions) >= 3:
                reason = f"Multiple actions ({len(same_screen_actions)}) returned to same screen"
                return True, reason
            elif len(current_screen_actions) >= 5:
                # Check if all recent actions stayed on same screen
                recent_actions = current_screen_actions[-5:]
                all_stayed = all(
                    a.get('to_screen_id') == from_screen_id or a.get('to_screen_id') is None 
                    for a in recent_actions if a.get('execution_success')
                )
                if all_stayed:
                    return True, "All recent actions stayed on same screen"
        
        return False, ""
