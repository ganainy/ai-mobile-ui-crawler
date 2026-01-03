from typing import Dict, Optional, Any

# Define the JSON output schema as a dictionary
# Supports multi-action batching: AI can return 1-12 actions to execute sequentially
JSON_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {

        "actions": {
            "type": "array",
            "description": "1-12 sequential actions. First must be valid from current screen.",
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
            "description": "Set true ONLY after completing signup/registration."
        }
    },
    "required": ["actions"]
}

# Fallback available actions (used only when config is not available)
_DEFAULT_AVAILABLE_ACTIONS = {
    "click": "Click on target element.",
    "input": "Type text into target (no need to click first).",
    "long_press": "Long press on target.",
    "scroll_down": "Scroll down to reveal content.",
    "scroll_up": "Scroll up to reveal content.",
    "swipe_left": "Swipe left.",
    "swipe_right": "Swipe right.",
    "back": "Press back button.",
    "double_tap": "Double tap (for zoom/galleries).",
    "clear_text": "Clear text from input.",
    "replace_text": "Replace text in input.",
    "flick": "Fast flick gesture.",
    "reset_app": "Reset app to initial state.",
    "fetch_email_otp": "Fetch OTP from email and type it.",
    "click_email_link": "Fetch and open verification link from email."
}

def get_available_actions(config: Optional[Any] = None) -> Dict[str, str]:
    """Get available actions from config, or return fallback defaults."""
    if config is not None:
        try:
            actions = config.CRAWLER_AVAILABLE_ACTIONS
            if actions and isinstance(actions, dict):
                return actions
        except Exception:
            pass
    return _DEFAULT_AVAILABLE_ACTIONS

# Editable part - users can customize this in the UI
ACTION_DECISION_SYSTEM_PROMPT = """# GOAL
AI testing agent maximizing app exploration coverage.

# PRIORITY
1. **Explore First**: Browse without login if possible (catalogs, menus, content)
2. **Defer Auth**: Skip login prompts, use "Guest"/"Skip" options when available
3. **Auth Last Resort**: Only login when features are completely blocked
   - Credentials: "{test_email}" / "{test_password}"
   - Set signup_completed: true after successful signup

# STRATEGY
- Prioritize unexplored screens/tabs/features
- Click into items, test interactive elements
- Escape repetition with different paths
- Use XML/OCR to identify elements precisely

# EXTERNAL LINKS
✅ Complete OAuth/SSO flows in browser when required
❌ Avoid: Privacy Policy, Terms, Help, Impressum, marketing links"""

# Fixed part - automatically appended by code
ACTION_DECISION_FIXED_PART = """
# MULTI-ACTION
Return 1-12 actions. Use multiple for confident sequences, single for new screens.

# OUTPUT SCHEMA
{json_schema}

# TARGET IDENTIFIERS
✅ Valid: "ocr_0", "username", "screen" (for scroll/back)
❌ Invalid: "android.widget.Button", UUIDs

# INPUT
- Direct typing (no click first): use "input" action
- Auth credentials: {test_email} / {test_password}
- Bounding box format: {{"top_left": [x1,y1], "bottom_right": [x2,y2]}}

# ACTIONS
{action_list}

# EXAMPLES
1. E-commerce launch → Browse products first, login only at checkout
2. Login modal → Click "Skip", continue exploring
3. Feature blocked → Now proceed with auth
4. OAuth redirect → Complete flow in browser, return to app"""

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