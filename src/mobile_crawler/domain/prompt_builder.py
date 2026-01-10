"""Prompt builder for AI interactions."""

import json
from typing import Dict, List, Optional

from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.domain.prompts import DEFAULT_SYSTEM_PROMPT
from mobile_crawler.infrastructure.step_log_repository import StepLog, StepLogRepository


class PromptBuilder:
    """Builds prompts for AI interactions with exploration context."""

    def __init__(self, config_manager: ConfigManager, step_log_repository: StepLogRepository):
        """Initialize prompt builder.

        Args:
            config_manager: Configuration manager for settings
            step_log_repository: Repository for step logs
        """
        self.config_manager = config_manager
        self.step_log_repository = step_log_repository

    def build_system_prompt(self) -> str:
        """Build the system prompt with test credentials.

        Returns:
            Complete system prompt string
        """
        # Get test credentials from config
        test_credentials = self._get_test_credentials()

        # Replace placeholders in the prompt
        prompt = DEFAULT_SYSTEM_PROMPT
        prompt = prompt.replace("{test_credentials}", test_credentials)
        prompt = prompt.replace("{stuck_status}", "{stuck_status}")  # Keep as placeholder
        
        return prompt

    def build_user_prompt(
        self,
        screenshot_b64: str,
        run_id: int,
        is_stuck: bool = False,
        stuck_reason: Optional[str] = None
    ) -> str:
        """Build the user prompt with current context.

        Args:
            screenshot_b64: Base64 encoded screenshot
            run_id: Current run ID
            is_stuck: Whether the crawler is currently stuck
            stuck_reason: Reason for being stuck

        Returns:
            JSON-formatted user prompt
        """
        # Get exploration journal
        journal = self._get_exploration_journal(run_id)

        # Get available actions
        available_actions = self._get_available_actions()

        # Build stuck status
        stuck_status = "STUCK" if is_stuck else "EXPLORING"
        if stuck_reason:
            stuck_status += f" - {stuck_reason}"

        # Format the user prompt
        prompt_data = {
            "screenshot": screenshot_b64,
            "exploration_journal": journal,
            "is_stuck": is_stuck,
            "stuck_reason": stuck_reason,
            "available_actions": available_actions
        }

        return json.dumps(prompt_data, indent=2)

    def _get_test_credentials(self) -> str:
        """Get test credentials from configuration.

        Returns:
            Formatted test credentials string
        """
        # Try to get test credentials from config
        test_username = self.config_manager.get('test_username', '')
        test_password = self.config_manager.get('test_password', '')
        test_email = self.config_manager.get('test_email', '')

        credentials = []
        if test_username:
            credentials.append(f"Username: {test_username}")
        if test_password:
            credentials.append(f"Password: {test_password}")
        if test_email:
            credentials.append(f"Email: {test_email}")

        if credentials:
            return "\n".join(credentials)
        else:
            return "No test credentials configured. Use default test values when encountering forms."

    def _get_exploration_journal(self, run_id: int) -> List[Dict]:
        """Get formatted exploration journal for the run.

        Args:
            run_id: Run ID to get journal for

        Returns:
            List of journal entries
        """
        step_logs = self.step_log_repository.get_exploration_journal(run_id, limit=15)

        journal = []
        for step in reversed(step_logs):  # Most recent first, but we want chronological
            entry = {
                "step": step.step_number,
                "action": step.action_description or step.action_type,
                "outcome": "Success" if step.execution_success else f"Failed: {step.error_message or 'Unknown error'}",
                "screen": f"Screen {step.to_screen_id}" if step.to_screen_id else "Unknown"
            }
            journal.append(entry)

        return journal

    def _get_available_actions(self) -> Dict[str, str]:
        """Get descriptions of available actions.

        Returns:
            Dictionary mapping action names to descriptions
        """
        return {
            "click": "Tap on a UI element at specified coordinates",
            "input": "Enter text into a text field",
            "long_press": "Long press on a UI element",
            "scroll_up": "Scroll up from center of screen",
            "scroll_down": "Scroll down from center of screen",
            "scroll_left": "Scroll left from center of screen",
            "scroll_right": "Scroll right from center of screen",
            "back": "Press the Android back button"
        }