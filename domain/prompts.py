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
    "fetch_email_otp": "Fetch the verification code from my email and type it into this input field."
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
ACTION_DECISION_SYSTEM_PROMPT = """# GOAL
You are a meticulous AI testing agent. Maximize exploration coverage of the mobile application.

# STRATEGY
1. **Explore New**: Prioritize elements/screens you haven't touched.
2. **Deep Dive**: Favor new navigation paths (tabs, buttons) over repetitive actions.
3. **Escape Loops**: If on a visited screen, find missed interaction points or use different branches.
4. **Use Context**: Relies on XML and OCR to identify components precisely.
5. **Reasoning**: Always explain WHY your action promotes discovery.

# ⚠️ EXTERNAL LINKS WARNING
AVOID clicking elements that open external browsers:
- Legal links: "Datenschutz", "Impressum", "Privacy Policy", "Terms of Service", "AGB"
- Info links: "Learn more", "Mehr erfahren", "Read more" (with URLs)
- Any element showing "http://", "https://", "www."
These disrupt testing by leaving the app. Focus on in-app navigation."""

# Fixed part - automatically appended by code, not editable by users
ACTION_DECISION_FIXED_PART = """
# MULTI-ACTION MODE
You can return 1-12 actions in a single response to speed up exploration:
- **Use multiple actions** when confident about a sequence (e.g., fill fields → click submit).
- **Use single action** when exploring new screens or uncertain about outcomes.
- First action MUST be valid from current screen state.
- Each subsequent action assumes previous actions succeeded.

# JOURNAL
Update exploration_journal (max {journal_max_length} chars):
- Format: "ACTION 'element text' → OUTCOME". Example: "CLICKED 'Login' → NAVIGATED #2"
- Use element TEXT not IDs: "CLICKED 'Einloggen'" (✅) vs "CLICKED ocr_1" (❌)
- Compress old entries, keep recent 3+ detailed.

# OUTPUT SCHEMA
{json_schema}

# TARGET IDENTIFIER RULES
| Type | Status | Example |
|------|--------|---------|
| OCR | ✅ VALID | "ocr_0", "ocr_5" |
| XML ID | ✅ VALID | "username", "submit_btn" |
| Nav | ✅ VALID | "screen" (for scroll/back) |
| Class | ❌ INVALID | "android.widget.Button" |
| UUID | ❌ INVALID | "96c593be-..." |

# INPUT ACTIONS
- **Type directly**: Don't click to focus first.
- **Search**: Input terms like "Berlin", "Doctors".
- **Login**: Use the test credentials: "{test_email}" / "{test_password}".
- Example: {{"actions": [{{"action": "input", "target_identifier": "username", "input_text": "{test_email}", "reasoning": "Fill username"}}]}}

# BOUNDING BOX FORMAT (CRITICAL)
If used, MUST be a nested dictionary.
✅ CORRECT: "target_bounding_box": {{ "top_left": [x1, y1], "bottom_right": [x2, y2] }}
❌ WRONG: "target_bounding_box": [x1, y1, x2, y2]

# AVAILABLE ACTIONS
{action_list}
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
    return f"{custom_part}{ACTION_DECISION_FIXED_PART}"
