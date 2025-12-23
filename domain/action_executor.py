"""
Action execution module for the AI agent.

Handles execution of all action types (click, input, scroll, etc.) with proper
argument handling and error recovery.
"""
import logging
from typing import Any, Callable, Dict, Optional

from config.numeric_constants import LONG_PRESS_MIN_DURATION_MS

logger = logging.getLogger(__name__)


class ActionExecutor:
    """
    Executes actions on the device through the Appium driver.
    
    Provides a clean interface between AI decisions and device interactions,
    handling argument normalization, validation, and execution.
    """
    
    def __init__(self, driver, config):
        """
        Initialize the ActionExecutor.
        
        Args:
            driver: AppiumDriver instance for device interaction
            config: Application configuration
        """
        self.driver = driver
        self.cfg = config
        self._init_action_dispatch_map()
    
    def _execute_click_action(self, action_data: Dict[str, Any]) -> bool:
        """Execute click action with proper argument handling."""
        target_id = action_data.get("target_identifier")
        bbox = action_data.get("target_bounding_box")
        
        # Pass target_identifier to driver.tap()
        # Element lookup is now the only supported method.
        return self.driver.tap(target_id, bbox)
    
    def _execute_input_action(self, action_data: Dict[str, Any]) -> bool:
        """Execute input action with proper argument handling.
        
        Uses tap + mobile:type for reliable input on both native and WebView elements.
        """
        target_id = action_data.get("target_identifier")
        bbox = action_data.get("target_bounding_box")
        input_text = action_data.get("input_text")
        
        if not target_id and not bbox:
            logger.error("Cannot execute input: No target identifier or bounding box provided")
            return False
        if input_text is None:
            input_text = ""  # Empty string for clear operations
        
        import time
        
        # Step 1: Tap to focus the input field
        if bbox:
            # OCR-based: use bounding box coordinates
            tap_success = self.driver.tap(target_id, bbox)
        else:
            # XML-based: use element tap
            tap_success = self.driver.tap(target_id, None)
        
        if not tap_success:
            logger.error(f"Failed to tap on input field: {target_id}")
            return False
        
        # Brief delay for keyboard to appear
        time.sleep(0.5)
        
        # Step 2: Use mobile: type for reliable text input (works on WebViews)
        try:
            driver = self.driver.helper.get_driver() if self.driver.helper else None
            if driver:
                driver.execute_script('mobile: type', {'text': input_text})
                return True
            else:
                logger.error("Driver not available for keyboard input")
                return False
        except Exception as e:
            logger.warning(f"mobile: type failed: {e}, trying fallback methods")
            
            # Fallback 1: ActionChains send_keys
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                driver = self.driver.helper.get_driver() if self.driver.helper else None
                if driver:
                    actions = ActionChains(driver)
                    actions.send_keys(input_text)
                    actions.perform()
                    return True
            except Exception as e2:
                logger.warning(f"ActionChains fallback failed: {e2}")
            
            # Fallback 2: Element send_keys (last resort)
            if not bbox and target_id:
                try:
                    return self.driver.input_text(target_id, input_text)
                except Exception as e3:
                    logger.error(f"All input methods failed: {e3}")
            
            return False

    
    def _execute_long_press_action(self, action_data: Dict[str, Any]) -> bool:
        """Execute long press action with proper argument handling."""
        target_id = action_data.get("target_identifier")
        bbox = action_data.get("target_bounding_box")
        # Default duration from config
        try:
            default_duration_ms = int(self.cfg.get('LONG_PRESS_MIN_DURATION_MS', LONG_PRESS_MIN_DURATION_MS))
        except Exception:
            default_duration_ms = LONG_PRESS_MIN_DURATION_MS
        duration_ms = action_data.get("duration_ms", default_duration_ms)
        
        # Prefer element-based long press via driver
        return self.driver.long_press(target_id or "", duration_ms)
    
    def _execute_double_tap_action(self, action_data: Dict[str, Any]) -> bool:
        """Execute double tap action with proper argument handling."""
        target_id = action_data.get("target_identifier")
        bbox = action_data.get("target_bounding_box")
        
        # Pass both target_identifier and bbox to driver.double_tap()
        return self.driver.double_tap(target_id, bbox)
    
    def _execute_clear_text_action(self, action_data: Dict[str, Any]) -> bool:
        """Execute clear text action with proper argument handling."""
        target_id = action_data.get("target_identifier")
        if not target_id:
            logger.error("Cannot execute clear_text: No target identifier provided")
            return False
        return self.driver.clear_text(target_id)
    
    def _execute_replace_text_action(self, action_data: Dict[str, Any]) -> bool:
        """Execute replace text action: tap, clear, then type new text."""
        target_id = action_data.get("target_identifier")
        bbox = action_data.get("target_bounding_box")
        input_text = action_data.get("input_text")
        
        if not target_id and not bbox:
            logger.error("Cannot execute replace_text: No target identifier provided")
            return False
        if input_text is None:
            logger.error("Cannot execute replace_text: No input_text provided")
            return False
        
        import time
        
        # Step 1: Tap to focus
        if bbox:
            tap_success = self.driver.tap(target_id, bbox)
        else:
            tap_success = self.driver.tap(target_id, None)
        
        if not tap_success:
            logger.error(f"Failed to tap on input field for replace: {target_id}")
            return False
        
        time.sleep(0.3)
        
        # Step 2: Clear existing text (select all + delete)
        try:
            driver = self.driver.helper.get_driver() if self.driver.helper else None
            if driver:
                # Try to clear using keyboard shortcuts
                driver.execute_script('mobile: performEditorAction', {'action': 'selectAll'})
                time.sleep(0.1)
        except Exception:
            pass  # Ignore if select all fails
        
        # Step 3: Type new text (replaces selection or appends)
        try:
            driver = self.driver.helper.get_driver() if self.driver.helper else None
            if driver:
                driver.execute_script('mobile: type', {'text': input_text})
                return True
        except Exception as e:
            logger.warning(f"mobile: type failed in replace: {e}")
            # Fall back to driver method
            if not bbox and target_id:
                return self.driver.replace_text(target_id, input_text)
        
        return False
    
    def _execute_flick_action(self, action_data: Dict[str, Any]) -> bool:
        """Execute flick action with proper argument handling."""
        # Try to get direction from action_data or infer from reasoning/target
        direction = action_data.get("direction")
        if not direction:
            # Try to infer from reasoning or target_identifier
            reasoning = action_data.get("reasoning", "").lower()
            target_id = action_data.get("target_identifier", "").lower()
            
            if "up" in reasoning or "up" in target_id:
                direction = "up"
            elif "down" in reasoning or "down" in target_id:
                direction = "down"
            elif "left" in reasoning or "left" in target_id:
                direction = "left"
            elif "right" in reasoning or "right" in target_id:
                direction = "right"
            else:
                # Default to down
                direction = "down"
        
        return self.driver.flick(direction.lower())
    
    def _execute_reset_app_action(self, action_data: Dict[str, Any]) -> bool:
        """Execute reset app action."""
        # reset_app doesn't need any parameters
        return self.driver.reset_app()

    def _init_action_dispatch_map(self):
        """Initialize the action dispatch map for efficient action execution."""
        self.action_dispatch_map = {
            "click": self._execute_click_action,
            "input": self._execute_input_action,
            "scroll_down": lambda action_data: self.driver.scroll("down"),
            "scroll_up": lambda action_data: self.driver.scroll("up"),
            "swipe_left": lambda action_data: self.driver.scroll("left"),
            "swipe_right": lambda action_data: self.driver.scroll("right"),
            "back": self.driver.press_back,
            "long_press": self._execute_long_press_action,
            "double_tap": self._execute_double_tap_action,
            "clear_text": self._execute_clear_text_action,
            "replace_text": self._execute_replace_text_action,
            "flick": self._execute_flick_action,
            "reset_app": self._execute_reset_app_action
        }
    
    def normalize_action_type(self, action_type: str, action_data: Dict[str, Any]) -> str:
        """
        Normalize generic action types to specific ones.
        
        Args:
            action_type: The action type string (may be generic like "scroll" or "swipe")
            action_data: The full action data dictionary for context
            
        Returns:
            Normalized action type string matching one of the supported actions
        """
        # If action is already specific, return as-is
        if action_type in self.action_dispatch_map:
            return action_type
        
        # Map generic actions to specific ones
        target_identifier = action_data.get("target_identifier", "").lower()
        reasoning = action_data.get("reasoning", "").lower()
        
        if action_type == "scroll":
            # Try to infer direction from context
            if "up" in target_identifier or "up" in reasoning:
                return "scroll_up"
            elif "down" in target_identifier or "down" in reasoning:
                return "scroll_down"
            else:
                # Default to scroll_down (most common)
                return "scroll_down"
        
        elif action_type == "swipe":
            # Try to infer direction from context
            if "left" in target_identifier or "left" in reasoning:
                return "swipe_left"
            elif "right" in target_identifier or "right" in reasoning:
                return "swipe_right"
            else:
                # Default to swipe_left (common for navigation)
                return "swipe_left"
        
        # Return original if no mapping found
        return action_type
    
    def execute_action(self, action_data: Dict[str, Any]) -> bool:
        """
        Execute an action based on the action_data dictionary.
        
        Args:
            action_data: Dictionary containing action information with at least an 'action' key.
                        Expected keys: action, target_identifier, target_bounding_box, input_text, etc.
        
        Returns:
            True if action executed successfully, False otherwise
        """
        try:
            # Get the action type
            action_type = action_data.get("action", "").lower()
            
            if not action_type:
                logger.error("Cannot execute action: No action type specified")
                return False
            
            # Map generic actions to specific ones if needed
            action_type = self.normalize_action_type(action_type, action_data)
            
            # Look up the handler in the dispatch map
            handler = self.action_dispatch_map.get(action_type)
            
            if not handler:
                logger.error(f"Unknown action type: {action_type}")
                return False
            
            # Execute the action using the handler
            if callable(handler):
                # If handler is a callable that takes action_data
                if action_type in ["back"]:
                    # back action doesn't take parameters
                    return handler()
                else:
                    return handler(action_data)
            else:
                logger.error(f"Action handler for {action_type} is not callable")
                return False
                
        except Exception as e:
            logger.error(f"Error executing action {action_data.get('action', 'unknown')}: {e}", exc_info=True)
            return False
