"""
Action execution module for the AI agent.

Handles execution of all action types (click, input, scroll, etc.) with proper
argument handling and error recovery.
"""
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from config.numeric_constants import LONG_PRESS_MIN_DURATION_MS

logger = logging.getLogger(__name__)


class ActionExecutor:
    """
    Executes actions on the device through the Appium driver.
    
    Provides a clean interface between AI decisions and device interactions,
    handling argument normalization, validation, and execution.
    """
    
    def __init__(self, driver, config, ai_helper: Optional[Callable[[str], str]] = None):
        """
        Initialize the ActionExecutor.
        
        Args:
            driver: AppiumDriver instance for device interaction
            config: Application configuration
            ai_helper: Optional callback to invoke AI for text processing (e.g. OTP extraction)
        """
        self.driver = driver
        self.cfg = config
        self.ai_helper = ai_helper
        self._init_action_dispatch_map()
    
    def _is_likely_resource_id(self, identifier: str) -> bool:
        """Check if identifier looks like a valid Android resource ID.
        
        Android resource IDs typically contain only:
        - Alphanumeric characters (a-z, A-Z, 0-9)
        - Underscores (_)
        - Dots (.) for package names
        - Colons (:) for resource type separation (e.g., com.app:id/button)
        - Forward slashes (/) for id separation
        - Hyphens (-) in some cases
        
        Display text (from OCR) usually contains:
        - Spaces
        - Unicode letters beyond basic ASCII
        - Special punctuation
        
        Returns:
            True if the identifier looks like a valid resource ID, False otherwise
        """
        import re
        
        if not identifier:
            return False
        
        # OCR IDs (ocr_X) are handled separately - not resource IDs
        if identifier.startswith("ocr_"):
            return False
        
        # Resource IDs should only contain: alphanumeric, underscore, dot, colon, slash, hyphen
        # This pattern matches valid Android resource ID characters
        resource_id_pattern = r'^[a-zA-Z0-9_.:/-]+$'
        
        if not re.match(resource_id_pattern, identifier):
            # Contains characters not valid in resource IDs (spaces, unicode, etc.)
            return False
        
        return True
    
    def _resolve_target_with_fallback(
        self, 
        action_data: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]], str]:
        """Resolve target with layered fallback strategy.
        
        Fallback order:
        1. Use target_identifier directly (element ID lookup)
        2. If ocr_X identifier → extract bounding box from ocr_results
        3. Use provided bounding box if available
        4. Try fuzzy matching for partial ID matches
        
        Args:
            action_data: Action data with target_identifier, target_bounding_box, 
                        and optionally ocr_results
            
        Returns:
            Tuple of (target_identifier, bounding_box, resolution_method)
            resolution_method: 'element_id', 'ocr_coordinates', 'bounding_box', 'fuzzy_match',
                              or 'none' if resolution failed
        """
        target_id = action_data.get("target_identifier")
        bbox = action_data.get("target_bounding_box")
        ocr_results = action_data.get("ocr_results", [])
        
        # Case 1: OCR identifier (ocr_X format) - resolve to coordinates
        if target_id and str(target_id).startswith("ocr_"):
            try:
                idx = int(str(target_id).split("_")[1])
                if ocr_results and 0 <= idx < len(ocr_results):
                    item = ocr_results[idx]
                    bounds = item.get('bounds')
                    if bounds and len(bounds) == 4:
                        resolved_bbox = {
                            "top_left": [bounds[0], bounds[1]],
                            "bottom_right": [bounds[2], bounds[3]]
                        }
                        text_hint = item.get('text', target_id)
                        logger.info(f"Resolved OCR target '{target_id}' to coordinates via text '{text_hint}'")
                        return target_id, resolved_bbox, 'ocr_coordinates'
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to resolve OCR target {target_id}: {e}")
            
            # OCR ID but couldn't resolve - try bounding box fallback
            if bbox:
                logger.info(f"OCR target '{target_id}' unresolved, using provided bounding box")
                return target_id, bbox, 'bounding_box'
            
            return target_id, None, 'none'
        
        # Case 2: Check if identifier looks like a resource ID or display text
        if target_id:
            if self._is_likely_resource_id(target_id):
                # Looks like a valid resource ID - use element lookup
                return target_id, bbox, 'element_id'
            else:
                # Looks like display text (from OCR) - prefer bounding box if available
                if bbox:
                    logger.info(f"Target '{target_id}' looks like display text, using bounding box coordinates")
                    return target_id, bbox, 'bounding_box'
                else:
                    # No bounding box, try element lookup as fallback (will likely fail)
                    logger.warning(f"Target '{target_id}' looks like display text but no bounding box provided, trying element lookup")
                    return target_id, bbox, 'element_id'
        
        # Case 3: No target ID but have bounding box
        if bbox:
            return None, bbox, 'bounding_box'
        
        return None, None, 'none'
    
    def _tap_with_fallback(
        self,
        action_data: Dict[str, Any]
    ) -> bool:
        """Execute tap with layered fallback.
        
        Tries:
        1. Element ID lookup
        2. If failed + OCR target → use OCR coordinates
        3. If failed + bounding box → tap coordinates
        4. If failed → try fuzzy XPath matching by text
        
        Returns:
            True if tap successful by any method
        """
        target_id, bbox, method = self._resolve_target_with_fallback(action_data)
        
        # Method 1: OCR coordinates - use coordinates directly
        if method == 'ocr_coordinates' and bbox:
            logger.info(f"Using OCR coordinates for target: {target_id}")
            return self.driver.tap(target_id, bbox)
        
        # Method 2: Element ID lookup
        if method == 'element_id' and target_id:
            try:
                # Try element lookup first
                success = self.driver.tap(target_id, None)
                if success:
                    return True
            except Exception as e:
                logger.warning(f"Element lookup failed for '{target_id}': {e}")
            
            # Fallback: use bounding box if provided
            if bbox:
                logger.info(f"Element '{target_id}' not found, using bounding box coordinates")
                return self.driver.tap(target_id, bbox)
            
            # Fallback: try to find element by text using XPath
            return self._tap_by_text_fallback(target_id, action_data)
        
        # Method 3: Bounding box only
        if method == 'bounding_box' and bbox:
            logger.info(f"Using bounding box coordinates for tap")
            return self.driver.tap(None, bbox)
        
        # No valid target
        logger.error("No valid target for tap action")
        return False
    
    def _tap_by_text_fallback(
        self, 
        target_id: str,
        action_data: Dict[str, Any]
    ) -> bool:
        """Fallback: try to find element by text matching.
        
        Searches for elements containing the target_id text or
        uses OCR label text for matching.
        """
        try:
            driver = self.driver.helper.get_driver() if self.driver.helper else None
            if not driver:
                return False
            
            # Extract potential text hints from target_id or reasoning
            reasoning = action_data.get("reasoning", "")
            ocr_results = action_data.get("ocr_results", [])
            
            # Try to find a text hint
            text_hint = None
            
            # Check if target_id contains useful text (after removing common prefixes)
            clean_id = target_id
            for prefix in ['field-', 'btn-', 'input-', 'text-', 'label-']:
                if clean_id.startswith(prefix):
                    clean_id = clean_id[len(prefix):]
                    break
            
            # Skip if it looks like a React-generated ID (contains :r or is very short)
            if ':r' in clean_id or len(clean_id) <= 3:
                # Try to extract text from OCR results that might match
                for ocr_item in ocr_results or []:
                    ocr_text = ocr_item.get('text', '')
                    # Look for matches in reasoning
                    if ocr_text and ocr_text.lower() in reasoning.lower():
                        text_hint = ocr_text
                        break
            else:
                text_hint = clean_id
            
            if not text_hint:
                logger.debug(f"No text hint found for fallback search of '{target_id}'")
                return False
            
            # Try XPath search by text
            from appium.webdriver.common.appiumby import AppiumBy
            
            # Try various text matching strategies
            xpath_patterns = [
                f'//*[@text="{text_hint}"]',
                f'//*[contains(@text, "{text_hint}")]',
                f'//*[@content-desc="{text_hint}"]',
                f'//*[contains(@content-desc, "{text_hint}")]',
            ]
            
            for xpath in xpath_patterns:
                try:
                    elements = driver.find_elements(AppiumBy.XPATH, xpath)
                    if elements:
                        # Tap the first visible element
                        for elem in elements:
                            try:
                                if elem.is_displayed():
                                    elem.click()
                                    logger.info(f"Fallback: tapped element by text '{text_hint}'")
                                    return True
                            except Exception:
                                continue
                except Exception:
                    continue
            
            logger.warning(f"Text fallback search failed for '{text_hint}'")
            return False
            
        except Exception as e:
            logger.error(f"Text fallback search error: {e}")
            return False
    
    def _execute_click_action(self, action_data: Dict[str, Any]) -> bool:
        """Execute click action with proper argument handling and fallbacks."""
        return self._tap_with_fallback(action_data)
    
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
        
        # Step 1: Tap to focus the input field (using fallback logic)
        tap_success = self._tap_with_fallback(action_data)
        
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
                    result = self.driver.input_text(target_id, input_text)
                    if result:
                        self.driver.hide_keyboard()
                    return result
                except Exception as e3:
                    logger.error(f"All input methods failed: {e3}")
            
            return False
        finally:
            # Always try to hide keyboard after successful input
            self.driver.hide_keyboard()

    
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
        
        # Step 1: Tap to focus (use fallback logic)
        tap_success = self._tap_with_fallback(action_data)
        
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
                self.driver.hide_keyboard()
                return True
        except Exception as e:
            logger.warning(f"mobile: type failed in replace: {e}")
            # Fall back to driver method
            if not bbox and target_id:
                result = self.driver.replace_text(target_id, input_text)
                self.driver.hide_keyboard()
                return result
        
        self.driver.hide_keyboard()
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

    def _execute_fetch_email_otp(self, action_data: Dict[str, Any]) -> bool:
        """
        Execute fetch email OTP action.
        
        Fetches code from Gmail and types it into the target element.
        """
        target_id = action_data.get("target_identifier")
        bbox = action_data.get("target_bounding_box")
        
        if not target_id and not bbox:
            logger.error("Cannot execute fetch_email_otp: No target identifier provided")
            return False
            
        # Get credentials from config
        # Fallback to TEST_EMAIL if GMAIL_USER is not set
        user = self.cfg.get('GMAIL_USER') or self.cfg.get('TEST_EMAIL')
        password = self.cfg.get('GMAIL_APP_PASSWORD')
        timeout = self.cfg.get('GMAIL_SEARCH_TIMEOUT', 60)
        
        if not user or not password:
            logger.error("Gmail credentials (GMAIL_APP_PASSWORD and either GMAIL_USER or TEST_EMAIL) not set")
            return False
            
        try:
            from infrastructure.gmail_service import GmailService
            service = GmailService(user, password)
            logger.info(f"Fetching OTP from Gmail for {user}...")
            
            # Helper to poll a few times if needed, or rely on service logic
            # For now, single call as service handles lookback
            # Pass min_timestamp to ensure we only get RECENT emails (ignore old runs)
            import time
            min_timestamp = time.time() - 120 # 2 minutes ago
            
            # Fetch raw content instead of code
            subject, body = service.fetch_latest_email_content(timeout=timeout, min_timestamp=min_timestamp)
            
            if not body:
                logger.warning("No email body found in Gmail")
                return False
                
            code = ""
            if self.ai_helper:
                # Use AI to extract code
                prompt = (
                    f"You are an OTP extraction assistant.\n"
                    f"Extract the verification code from the following email.\n"
                    f"Subject: {subject}\n"
                    f"Body:\n{body}\n\n"
                    f"Return ONLY the code (digits). Do not return any other text."
                )
                logger.info(f"Asking AI to extract OTP from email '{subject}'...")
                code = self.ai_helper(prompt).strip()
                # loose cleanup in case AI is chatty
                import re
                match = re.search(r'\d{4,8}', code)
                if match:
                    code = match.group(0)
            else:
                # Fallback to simple regex if no AI helper available
                logger.warning("No AI helper available for OTP extraction, using fallback regex.")
                import re
                match = re.search(r'\b\d{4,8}\b', body)
                if match:
                    code = match.group(0)

            if not code:
                logger.warning("No OTP code extracted from email")
                return False
                
            logger.info(f"OTP extracted: {code}. Typing into target...")
            
            # Construct synthetic input action to reuse input logic
            input_action_data = action_data.copy()
            input_action_data['action'] = 'input'
            input_action_data['input_text'] = code
            
            return self._execute_input_action(input_action_data)
            
        except Exception as e:
            logger.error(f"Failed to fetch/enter email OTP: {e}", exc_info=True)
            return False

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
            "reset_app": self._execute_reset_app_action,
            "fetch_email_otp": self._execute_fetch_email_otp
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
    
    def execute_action_batch(
        self,
        actions: List[Dict[str, Any]],
        wait_between_actions: float = 0.5,
        stop_on_error: bool = True
    ) -> Tuple[int, List[bool], Optional[str]]:
        """Execute a batch of actions sequentially.
        
        This enables multi-action mode where the AI can return multiple actions
        to be executed in sequence, reducing AI calls and speeding up crawling.
        
        Args:
            actions: List of action data dictionaries
            wait_between_actions: Delay between actions in seconds
            stop_on_error: If True, stop executing on first failure
            
        Returns:
            Tuple of (actions_executed_count, success_list, error_message)
            - actions_executed_count: Number of actions that were attempted
            - success_list: List of success/failure booleans for each action
            - error_message: Error description if stopped early, None otherwise
        """
        import time
        
        if not actions:
            return 0, [], "No actions provided"
        
        success_list: List[bool] = []
        error_message: Optional[str] = None
        
        for i, action_data in enumerate(actions):
            action_type = action_data.get("action", "unknown")
            target = action_data.get("target_identifier", "no-target")
            
            logger.info(f"Executing batch action {i + 1}/{len(actions)}: {action_type} on '{target}'")
            
            try:
                success = self.execute_action(action_data)
                success_list.append(success)
                
                if not success:
                    error_message = f"Action {i + 1} ({action_type}) failed on '{target}'"
                    logger.warning(error_message)
                    
                    if stop_on_error:
                        logger.info(f"Stopping batch execution at action {i + 1} (stop_on_error=True)")
                        break
                
                # Wait between actions (except after the last one)
                if i < len(actions) - 1:
                    # Robustly ensure keyboard is hidden between batched actions
                    try:
                        self.driver.hide_keyboard()
                    except Exception:
                        pass
                    time.sleep(wait_between_actions)
                    
            except Exception as e:
                error_message = f"Action {i + 1} ({action_type}) raised exception: {e}"
                logger.error(error_message, exc_info=True)
                success_list.append(False)
                
                if stop_on_error:
                    break
        
        executed_count = len(success_list)
        logger.info(f"Batch execution complete: {sum(success_list)}/{executed_count} actions succeeded")
        
        return executed_count, success_list, error_message

