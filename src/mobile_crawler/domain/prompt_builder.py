"""Prompt builder for AI interactions."""

import json

from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.domain.prompts import DEFAULT_SYSTEM_PROMPT
from mobile_crawler.infrastructure.app_account_store import AppAccount, AppAccountStore
from mobile_crawler.infrastructure.screen_repository import ScreenRepository
from mobile_crawler.infrastructure.step_log_repository import StepLogRepository
from mobile_crawler.infrastructure.verification_inbox import VerificationInboxStore, default_signup_address


def get_app_account(config_manager: ConfigManager, app_package: str | None) -> AppAccount | None:
    """Get the App Account stored for `app_package`, if any."""
    if not app_package:
        return None
    return AppAccountStore(config_manager.user_config_store).get(app_package)


def get_form_email(config_manager: ConfigManager, app_package: str | None) -> str:
    """Email for form fields: the App Account's override, else the Verification Inbox sign-up address, else ''."""
    if not app_package:
        return ""
    account = get_app_account(config_manager, app_package)
    if account and account.address_override:
        return account.address_override
    inbox = VerificationInboxStore(config_manager.user_config_store).get()
    return default_signup_address(inbox.address, app_package) if inbox else ""


def get_form_phone(config_manager: ConfigManager) -> str:
    """Phone for form fields: the manual Mobile Number, else the number detected from the device."""
    return str(config_manager.get("test_phone", "") or config_manager.get("detected_phone", "") or "")


def format_login_and_form_data(config_manager: ConfigManager, app_package: str | None) -> str:
    """Format the package's App Account plus Form Fill Data for an agent prompt.

    Says clearly when no App Account exists so the agent does not invent one.
    """
    lines = []
    account = get_app_account(config_manager, app_package)
    if account:
        lines.append(f"Username: {account.username}")
        lines.append(f"Password: {account.password}")
    else:
        target = app_package or "this app"
        lines.append(
            f"No App Account exists for {target}. Do not invent login credentials; "
            "sign up if the app allows it, otherwise explore what is reachable without logging in."
        )

    for label, value in (
        ("Address", config_manager.get("test_address", "")),
        ("Email", get_form_email(config_manager, app_package)),
        ("Phone Number", get_form_phone(config_manager)),
    ):
        if value:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


class PromptBuilder:
    """Builds prompts for AI interactions with exploration context."""

    def __init__(
        self,
        config_manager: ConfigManager,
        step_log_repository: StepLogRepository,
        screen_repository: ScreenRepository | None = None,
    ):
        """Initialize prompt builder.

        Args:
            config_manager: Configuration manager for settings
            step_log_repository: Repository for step logs
            screen_repository: Optional repository for screen info (enables novelty signals)
        """
        self.config_manager = config_manager
        self.step_log_repository = step_log_repository
        self.screen_repository = screen_repository

    def build_system_prompt(self, app_package: str | None = None) -> str:
        """Build the system prompt with the package's App Account and form fill data.

        Args:
            app_package: Package being crawled; selects which App Account is shown

        Returns:
            Complete system prompt string
        """
        test_credentials = self._get_test_credentials(app_package)

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
        stuck_reason: str | None = None,
        current_screen_id: int | None = None,
        current_screen_is_new: bool | None = None,
        total_unique_screens: int | None = None,
        screen_dimensions: dict[str, int] | None = None,
        app_package: str | None = None,
    ) -> str:
        """Build the user prompt with current context.

        Args:
            screenshot_b64: Base64 encoded screenshot
            run_id: Current run ID
            is_stuck: Whether the crawler is currently stuck
            stuck_reason: Reason for being stuck
            current_screen_id: ID of the current screen (for novelty context)
            current_screen_is_new: Whether the current screen is newly discovered
            total_unique_screens: Total unique screens discovered so far
            screen_dimensions: Original screen dimensions {"width": W, "height": H}
            app_package: Package being crawled (unused)

        Returns:
            JSON-formatted user prompt
        """
        # Get exploration journal with novelty info
        journal = self._get_exploration_journal(run_id)

        # Get available actions
        available_actions = self._get_available_actions()

        # Build stuck status
        stuck_status = "STUCK" if is_stuck else "EXPLORING"
        if stuck_reason:
            stuck_status += f" - {stuck_reason}"

        # Build exploration progress summary
        exploration_progress = self._build_exploration_progress(
            run_id=run_id,
            current_screen_id=current_screen_id,
            current_screen_is_new=current_screen_is_new,
            total_unique_screens=total_unique_screens,
        )

        # Format the user prompt
        prompt_data = {
            "screenshot": screenshot_b64,
            "screen_dimensions": screen_dimensions or {"width": 1080, "height": 2400},
            "exploration_progress": exploration_progress,
            "exploration_journal": journal,
            "is_stuck": is_stuck,
            "stuck_reason": stuck_reason,
            "available_actions": available_actions,
        }

        return json.dumps(prompt_data, indent=2)

    def _build_exploration_progress(
        self,
        run_id: int,
        current_screen_id: int | None = None,
        current_screen_is_new: bool | None = None,
        total_unique_screens: int | None = None,
    ) -> dict:
        """Build exploration progress summary for the AI.

        Args:
            run_id: Current run ID
            current_screen_id: ID of the current screen
            current_screen_is_new: Whether current screen is new
            total_unique_screens: Total unique screens discovered

        Returns:
            Dictionary with exploration progress metrics
        """
        progress = {}

        # Add current screen context
        if current_screen_id is not None:
            progress["current_screen_id"] = current_screen_id
            progress["current_screen_status"] = (
                "NEW - First time seeing this screen!"
                if current_screen_is_new
                else "REVISITED - Already explored this screen"
            )

        # Add total unique screens
        if total_unique_screens is not None:
            progress["unique_screens_discovered"] = total_unique_screens

        # Add step count
        step_stats = self.step_log_repository.get_step_statistics(run_id)
        progress["total_steps"] = step_stats.get("total_steps", 0)
        progress["successful_actions"] = step_stats.get("successful_steps", 0)
        progress["failed_actions"] = step_stats.get("failed_steps", 0)

        # Calculate exploration efficiency
        if progress.get("total_steps", 0) > 0 and progress.get("unique_screens_discovered", 0) > 0:
            efficiency = progress["unique_screens_discovered"] / progress["total_steps"]
            progress["exploration_hint"] = self._get_exploration_hint(efficiency, current_screen_is_new)

        return progress

    def _get_exploration_hint(self, efficiency: float, current_screen_is_new: bool | None) -> str:
        """Generate a hint to guide exploration strategy.

        Args:
            efficiency: Ratio of unique screens to total steps
            current_screen_is_new: Whether current screen is new

        Returns:
            Hint string for the AI
        """
        if current_screen_is_new:
            return "Great! You discovered a new screen. Explore all interactive elements here before moving on."
        elif efficiency < 0.3:
            return "Low discovery rate. Try different actions: scroll to reveal hidden content, use back button, or try unexplored navigation paths."
        elif efficiency < 0.5:
            return "Moderate discovery. Look for untapped buttons, menus, or navigation elements."
        else:
            return "Good exploration efficiency. Continue systematic coverage."

    def _get_test_credentials(self, app_package: str | None = None) -> str:
        """Format the package's App Account plus generic Form Fill Data."""
        return format_login_and_form_data(self.config_manager, app_package)

    def _get_exploration_journal(self, run_id: int) -> list[dict]:
        """Get formatted exploration journal for the run with screen novelty info.

        Args:
            run_id: Run ID to get journal for

        Returns:
            List of journal entries with novelty signals
        """
        step_logs = self.step_log_repository.get_exploration_journal(run_id, limit=15)

        # Track which screens we've seen to determine novelty in the journal
        seen_screens: set[int] = set()

        journal = []
        for step in step_logs:  # Already in chronological order from repository
            # Determine screen novelty (first occurrence in journal = new at that time)
            screen_id = step.to_screen_id
            is_new_in_journal = False

            if screen_id is not None:
                if screen_id not in seen_screens:
                    is_new_in_journal = True
                    seen_screens.add(screen_id)

            # Build journal entry with novelty signal
            outcome = "Success" if step.execution_success else f"Failed: {step.error_message or 'Unknown error'}"
            entry = {
                "step": step.step_number,
                "action": step.action_description or step.action_type,
                "outcome": outcome,
            }

            # Add screen info with novelty signal
            if screen_id is not None:
                entry["screen"] = f"Screen #{screen_id}"
                entry["screen_status"] = "NEW" if is_new_in_journal else "revisited"
            else:
                entry["screen"] = "Unknown"

            journal.append(entry)

        return journal

    def _get_available_actions(self) -> dict[str, str]:
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
            "back": "Press the Android back button",
        }
