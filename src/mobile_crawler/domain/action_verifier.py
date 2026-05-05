"""Post-action verification for UI state transitions.

Compares pre-action and post-action UI state to confirm
the expected transition occurred.
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Set

logger = logging.getLogger(__name__)

# Actions that are expected to change the UI state
NAVIGATION_ACTIONS: Set[str] = {
    "back", "home", "click", "tap", "start_app", "launch_app",
    "recent_apps",
}


class StateProvider(Protocol):
    """Protocol for UI state capture."""
    async def get_state(self) -> Any: ...


class Driver(Protocol):
    """Protocol for current app detection."""
    async def _get_current_app(self) -> str: ...


@dataclass
class VerificationResult:
    """Result of post-action UI state verification."""
    verified: bool
    package_changed: bool
    ui_tree_changed: bool
    details: str

    def __str__(self) -> str:
        return (
            f"VerificationResult(verified={self.verified}, "
            f"pkg_changed={self.package_changed}, "
            f"ui_changed={self.ui_tree_changed}, "
            f"details='{self.details}')"
        )


class ActionVerifier:
    """Verifies that an action produced the expected UI change.

    Captures pre-action UI state, then compares with post-action state.
    Navigation actions (back, home, click, start_app) are expected to
    change the UI. Non-navigation actions (scroll, input) may not visibly
    change the UI and are verified leniently.
    """

    def __init__(self, state_provider: StateProvider, driver: Driver):
        """
        Args:
            state_provider: Object with async get_state() returning UIState
                            with formatted_text and elements attributes.
            driver: Object with async _get_current_app() returning package name.
        """
        self.state_provider = state_provider
        self.driver = driver

    async def capture_pre_state(self) -> Dict[str, Any]:
        """Capture UI state before action.

        Returns:
            Dict with keys: package (str), ui_text_hash (int),
            element_count (int). Returns empty dict on error.
        """
        try:
            ui_state = await self.state_provider.get_state()
            current_app = await self.driver._get_current_app()
            formatted_text = getattr(ui_state, "formatted_text", "")
            elements = getattr(ui_state, "elements", [])

            return {
                "package": current_app or "",
                "ui_text_hash": hash(formatted_text),
                "element_count": len(elements) if elements else 0,
            }
        except Exception as e:
            logger.warning(f"Failed to capture pre-action state: {e}")
            return {}

    async def verify(
        self,
        pre_state: Dict[str, Any],
        action_type: str,
    ) -> VerificationResult:
        """Verify post-action state changed as expected.

        Args:
            pre_state: Dict from capture_pre_state().
            action_type: The action that was executed.

        Returns:
            VerificationResult with verified, package_changed, ui_tree_changed, details.
        """
        if not pre_state:
            # Could not capture pre-state, cannot verify
            return VerificationResult(
                verified=True,  # Assume OK when we can't verify
                package_changed=False,
                ui_tree_changed=False,
                details="pre_state unavailable, skipping verification",
            )

        post_state = await self.capture_pre_state()

        if not post_state:
            return VerificationResult(
                verified=True,
                package_changed=False,
                ui_tree_changed=False,
                details="post_state unavailable, skipping verification",
            )

        package_changed = pre_state.get("package") != post_state.get("package")
        ui_changed = pre_state.get("ui_text_hash") != post_state.get("ui_text_hash")

        # Navigation actions MUST change state
        # Non-navigation actions MAY change state
        if action_type in NAVIGATION_ACTIONS:
            verified = package_changed or ui_changed
        else:
            verified = True  # Scrolls, input may not visibly change

        details = (
            f"pre_pkg={pre_state.get('package', '?')} "
            f"post_pkg={post_state.get('package', '?')} "
            f"ui_changed={ui_changed}"
        )

        if not verified:
            logger.warning(
                f"Navigation action '{action_type}' did not change UI state. "
                f"{details}"
            )

        return VerificationResult(
            verified=verified,
            package_changed=package_changed,
            ui_tree_changed=ui_changed,
            details=details,
        )
