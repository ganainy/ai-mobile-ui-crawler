from typing import Dict, Optional, Any

# Define the JSON output schema as a dictionary
JSON_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "exploration_journal": {
            "type": "string",
            "description": "Updated exploration journal. Include what happened from your action. Compress older entries if needed to fit within the character limit."
        },
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
        "reasoning": {"type": "string"},
    },
    "required": ["exploration_journal", "action", "target_identifier", "reasoning"]
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
    "reset_app": "Reset the app to its initial state (clears app data and restarts)."
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
ACTION_DECISION_SYSTEM_PROMPT = """You are a meticulous AI testing agent. Your goal is to maximize the exploration coverage of the mobile application.
Strategize your actions to:
1. Prioritize interacting with elements you haven't touched before on this screen.
2. Favor deep exploration by following new navigation paths (buttons, menu items, tabs) over repetitive actions.
3. If you detect you are on a previously visited screen, look for missed interaction points or use different navigation branches to escape cycles.
4. Use the provided XML and OCR context to identify all interactive components precisely.
5. Provide clear reasoning for why your chosen action promotes further discovery of the app's features and states."""

# Fixed part - automatically appended by code, not editable by users
ACTION_DECISION_FIXED_PART = """
EXPLORATION JOURNAL RULES:
- You MUST output an updated exploration_journal that records your actions and their outcomes
- Maximum journal length: {journal_max_length} characters
- FORMAT REQUIRED - Each entry must include:
  • What action you took with DESCRIPTIVE TEXT: "CLICKED 'Login' button" or "INPUT 'email@test.com' in 'Email' field"
  • The ACTUAL outcome from LAST ACTION OUTCOME section: "→ NAVIGATED to screen #X" or "→ STAYED (no effect)"
  • Brief observations about the current screen
- IMPORTANT: Use the actual text of elements, not opaque IDs. Write "CLICKED 'Einloggen'" not "CLICKED ocr_1"
- Example format: "CLICKED 'Login' → NAVIGATED #2 (password screen). INPUT password → STAYED (form not submitted yet)."
- When approaching limit, compress OLDEST entries but keep:
  • Dead-ends to avoid (actions with STAYED/no effect)
  • Last 3+ actions with full detail
- On first action (empty journal), describe the initial screen state
- CRITICAL: Check the LAST ACTION OUTCOME section and record exactly what it says happened

Use the following JSON schema to structure your output:
{json_schema}

IMPORTANT - target_identifier rules:
- For OCR context: Use exact "ocr_X" IDs (e.g., "ocr_0", "ocr_5") as target_identifier
- For XML context: Use ONLY the resource-id attribute (e.g., "addMedication", "ctaButton")
- NEVER use class names like "android.widget.Button" or "android.view.View" - these are NOT valid identifiers
- For scroll/swipe/back actions: Use "screen" as the target_identifier

INPUT ACTION RULES:
- When you see an EditText or input field, use action="input" with input_text filled
- DO NOT just "click" on input fields to "test" them - directly use INPUT action
- For search fields: INPUT a relevant search term (e.g., "Zahnarzt", "Berlin")
- For login fields: Use credentials if provided, otherwise use test values like "test@email.com"
- Example: {{"action": "input", "target_identifier": "ocr_1", "input_text": "Berlin"}}

Available actions:
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
