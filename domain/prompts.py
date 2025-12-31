from typing import Dict, Optional, Any

# Define the JSON output schema as a dictionary
# Supports multi-action batching: AI can return 1-12 actions to execute sequentially
JSON_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "exploration_journal": {
            "type": "string",
            "description": "Updated exploration journal. Include what happened from your actions. Compress older entries if needed to fit within the character limit."
        },
        "actions": {
            "type": "array",
            "description": "Array of 1-12 actions to execute sequentially. First action MUST be valid from current screen. Each subsequent action assumes previous actions succeeded.",
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "target_identifier": {"type": "string"},
                    "target_bounding_box": {
                        "type": ["object", "null"],
                        "properties": {
                            "top_left": {"type": "array", "items": {"type": "number"}},
                            "bottom_right": {"type": "array", "items": {"type": "number"}}
                        }
                    },
                    "input_text": {"type": ["string", "null"]},
                    "reasoning": {"type": "string"}
                },
                "required": ["action", "target_identifier", "reasoning"]
            },
            "minItems": 1,
            "maxItems": 12
        },
        "signup_completed": {
            "type": "boolean",
            "description": "Set to true ONLY when you have just successfully completed a signup/registration flow. This triggers credential storage for future logins."
        }
    },
    "required": ["exploration_journal", "actions"]
}

# Fallback available actions (used only when config is not available)
# This should match CRAWLER_AVAILABLE_ACTIONS in config/app_config.py
_DEFAULT_AVAILABLE_ACTIONS = {
    "click": "Perform a click action on the target element.",
    "input": "Tap on the element to focus it, then type the provided text (no need to click first).",
    "long_press": "Perform a long press action on the target element.",
    "scroll_down": "Scroll the view downward to reveal more content below.",
    "scroll_up": "Scroll the view upward to reveal more content above.",
    "swipe_left": "Swipe left to navigate or reveal content on the right.",
    "swipe_right": "Swipe right to navigate or reveal content on the left.",
    "back": "Press the back button to return to the previous screen.",
    "double_tap": "Perform a double tap gesture on the target element (useful for zooming, image galleries).",
    "clear_text": "Clear all text from the target input element.",
    "replace_text": "Tap on the input element, clear existing text, and type new text.",
    "flick": "Perform a fast flick gesture in the specified direction (faster than scroll for quick navigation).",
    "reset_app": "Reset the app to its initial state (clears app data and restarts).",
    "fetch_email_otp": "Fetch the verification code from my email and type it into this input field.",
    "click_email_link": "Fetch the activation/verification link from my email and open it on the device."
}

def get_available_actions(config: Optional[Any] = None) -> Dict[str, str]:
    """Get available actions from config, or return fallback defaults.
    
    Args:
        config: Optional Config instance. If provided, uses CRAWLER_AVAILABLE_ACTIONS.
                If None or config returns empty, returns fallback defaults.
    
    Returns:
        Dictionary mapping action names to descriptions
    """
    if config is not None:
        try:
            actions = config.CRAWLER_AVAILABLE_ACTIONS
            if actions and isinstance(actions, dict):
                return actions
        except Exception:
            pass
    
    return _DEFAULT_AVAILABLE_ACTIONS

# Backward compatibility: export as AVAILABLE_ACTIONS for existing imports
# This will be removed in a future version - use get_available_actions() instead
AVAILABLE_ACTIONS = _DEFAULT_AVAILABLE_ACTIONS

# Define prompt templates as string constants
# Editable part - users can customize this in the UI
ACTION_DECISION_SYSTEM_PROMPT = """# PRIMARY GOAL
You are a meticulous AI testing agent. Your PRIMARY objective is to maximize exploration coverage of the mobile application's features and content.

# EXPLORATION PRIORITY HIERARCHY
1. **Explore First, Authenticate Later**: If the app allows browsing/exploring without login, DO THAT FIRST
   - Browse product catalogs, view listings, read content, navigate menus
   - Only pursue login/signup when you hit a hard wall requiring authentication
   - Example: E-commerce apps often let you browse products before requiring login for checkout

2. **Defer Authentication**: Treat login/signup as a LAST RESORT, not a first step
   - Skip "Login" prompts if there's a "Skip", "Browse as Guest", "Continue without account" option
   - Dismiss login overlays/modals to continue exploring
   - Only authenticate when essential features are completely blocked

3. **When Authentication is Unavoidable**:
   - Try to explore as much as possible before authenticating
   - Use provided test credentials: "{test_email}" / "{test_password}"
   - Complete the signup/registration flow (set signup_completed: true when done)
   - If signup requires external browser, follow through and complete it there

# EXPLORATION STRATEGY
1. **Discover New Territory**: Prioritize unexplored screens, tabs, and features
2. **Deep Feature Testing**: Click into items, open details, test interactive elements
3. **Comprehensive Coverage**: Navigate through all tabs, menus, categories
4. **Escape Repetition**: If revisiting a screen, find different interaction paths
5. **Context-Aware**: Use XML hierarchy and OCR text to identify elements precisely

# EXTERNAL BROWSER HANDLING
**When External Browsers are REQUIRED** (e.g., OAuth, SSO, mandatory signup):
- ✅ FOLLOW THROUGH: Complete the authentication flow in external browser
- ✅ USE CREDENTIALS: Enter test email/password when prompted
- ✅ COMPLETE SIGNUP: Fill all required forms, verify email if needed
- ✅ RETURN TO APP: After successful auth, return to app to continue exploration

**When External Links are OPTIONAL** (e.g., info pages, marketing):
- ❌ AVOID: "Privacy Policy", "Terms of Service", "Learn More", "Help Center"
- ❌ AVOID: "Impressum", "Datenschutz", "AGB" (legal pages)
- ❌ AVOID: Marketing links showing "http://", "https://", "www."
- These disrupt testing by taking you out of the app without benefit

# REASONING PRINCIPLE
Always explain WHY your action advances exploration coverage or removes authentication barriers when necessary."""

# Fixed part - automatically appended by code, not editable by users
ACTION_DECISION_FIXED_PART = """
# MULTI-ACTION MODE
You can return 1-12 actions in a single response to speed up exploration:
- **Use multiple actions** when confident about a sequence (e.g., fill form fields → submit → verify email).
- **Use single action** when exploring new screens or uncertain about outcomes.
- First action MUST be valid from current screen state.
- Each subsequent action assumes previous actions succeeded.

# JOURNAL UPDATES
Update exploration_journal (max {journal_max_length} chars):
- Format: "ACTION 'element text' → OUTCOME". Example: "CLICKED 'Search' → OPENED search page #15"
- Use element TEXT not IDs: "TAPPED 'Products' tab" (✅) vs "TAPPED ocr_3" (❌)
- Track exploration progress: "Explored 8/12 tabs, browsed 15 product listings without login"
- Compress old entries, keep recent 3-5 detailed entries
- Note when authentication becomes necessary: "Hit paywall on checkout, proceeding with login"

# OUTPUT SCHEMA
{json_schema}

# TARGET IDENTIFIER RULES
| Type | Status | Example | Usage |
|------|--------|---------|-------|
| OCR | ✅ VALID | "ocr_0", "ocr_5" | For visible text elements |
| XML ID | ✅ VALID | "username", "submit_btn" | For elements with resource-id |
| Nav | ✅ VALID | "screen" | For scroll/back/swipe actions |
| Class | ❌ INVALID | "android.widget.Button" | Too generic, don't use |
| UUID | ❌ INVALID | "96c593be-..." | Internal IDs, don't use |

# INPUT ACTIONS
- **Direct typing**: Don't click to focus first, just use "input" action
- **Search queries**: Use realistic search terms like "Berlin doctors", "iPhone 15", "pizza delivery"
- **Authentication**: Use test credentials ONLY when required:
  - Email: "{test_email}"
  - Password: "{test_password}"
- **Multi-step forms**: Chain actions for efficiency
  Example: {{"actions": [
    {{"action": "input", "target_identifier": "email", "input_text": "{test_email}", "reasoning": "Fill email for required signup"}},
    {{"action": "input", "target_identifier": "password", "input_text": "{test_password}", "reasoning": "Fill password"}},
    {{"action": "click", "target_identifier": "signup_button", "reasoning": "Submit signup form"}}
  ]}}

# BOUNDING BOX FORMAT (CRITICAL)
If used, MUST be a nested dictionary with explicit keys:
✅ CORRECT: "target_bounding_box": {{"top_left": [x1, y1], "bottom_right": [x2, y2]}}
❌ WRONG: "target_bounding_box": [x1, y1, x2, y2]
❌ WRONG: "target_bounding_box": {{"coords": [x1, y1, x2, y2]}}

# AVAILABLE ACTIONS
{action_list}

# DECISION-MAKING EXAMPLES

## Scenario 1: E-commerce App Launch
Screen shows: Product grid with "Login" button in top-right
✅ CORRECT: Click on products to browse, explore categories, only login when trying to checkout
❌ WRONG: Immediately click "Login" button

## Scenario 2: Login Modal Appears
Modal shows: "Login to continue" with "Skip" button
✅ CORRECT: Click "Skip" or close modal, continue exploring
❌ WRONG: Fill login form without exploring first

## Scenario 3: Feature Requires Auth
Tried to add item to cart, got "Please login" message
✅ CORRECT: Now proceed with login since feature is blocked
❌ WRONG: Keep trying to bypass without authenticating

## Scenario 4: External Browser for OAuth
App redirects to Google Sign In browser page
✅ CORRECT: Complete Google OAuth flow, return to app
❌ WRONG: Press back button, giving up on authentication

## Scenario 5: Explored Most Features
Explored 90% of app, only "Messages" tab requires login
✅ CORRECT: Now login to unlock remaining 10% for complete coverage
❌ WRONG: Stop exploration without accessing locked features
"""

def build_action_decision_prompt(custom_part: Optional[str] = None) -> str:
    """Build the full action decision prompt by combining custom and fixed parts.
    
    Args:
        custom_part: Custom prompt text from user (editable part). If None, uses default.
    
    Returns:
        Complete prompt string with both custom and fixed parts
    """
    if custom_part is None:
        custom_part = ACTION_DECISION_SYSTEM_PROMPT
    
    # Combine custom part with fixed part
    return f"{custom_part}\n{ACTION_DECISION_FIXED_PART}"


# Additional helper function for authentication decision logic
def should_attempt_authentication(exploration_state: Dict[str, Any]) -> bool:
    """Determine if authentication should be attempted based on exploration state.
    
    Args:
        exploration_state: Dictionary containing:
            - screens_explored: Number of unique screens visited
            - features_blocked: Number of features requiring auth
            - guest_features_remaining: Estimated unexplored guest-accessible features
    
    Returns:
        Boolean indicating whether to proceed with authentication
    """
    screens_explored = exploration_state.get('screens_explored', 0)
    features_blocked = exploration_state.get('features_blocked', 0)
    guest_features_remaining = exploration_state.get('guest_features_remaining', 0)
    
    # Don't authenticate if we haven't explored much yet
    if screens_explored < 3:
        return False
    
    # Don't authenticate if there are still guest features to explore
    if guest_features_remaining > 0:
        return False
    
    # Authenticate if multiple features are blocked
    if features_blocked >= 2:
        return True
    
    # Authenticate if we've explored extensively and hit a wall
    if screens_explored >= 10 and features_blocked >= 1:
        return True
    
    return False