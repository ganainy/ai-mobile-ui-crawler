"""Screen state management for mobile applications."""

import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from mobile_crawler.infrastructure.appium_driver import AppiumDriver
from mobile_crawler.infrastructure.element_finder import ElementFinder, UIElement
from mobile_crawler.infrastructure.screenshot_capture import ScreenshotCapture

logger = logging.getLogger(__name__)


class ScreenState(Enum):
    """Possible screen states."""
    LOADING = "loading"
    READY = "ready"
    INTERACTING = "interacting"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ScreenSnapshot:
    """Snapshot of screen state at a point in time."""
    timestamp: float
    screenshot_path: Optional[str]
    elements: List[UIElement]
    screen_state: ScreenState
    activity_name: Optional[str]
    package_name: Optional[str]
    screen_bounds: Tuple[int, int, int, int]  # left, top, right, bottom
    metadata: Dict[str, Any]


class ScreenStateManager:
    """Manages screen state detection and transitions."""

    def __init__(self, appium_driver: AppiumDriver,
                 element_finder: Optional[ElementFinder] = None,
                 screenshot_capture: Optional[ScreenshotCapture] = None):
        """Initialize screen state manager.

        Args:
            appium_driver: AppiumDriver instance
            element_finder: ElementFinder instance (optional)
            screenshot_capture: ScreenshotCapture instance (optional)
        """
        self.driver = appium_driver
        self.element_finder = element_finder or ElementFinder(appium_driver)
        self.screenshot_capture = screenshot_capture or ScreenshotCapture(appium_driver)

        self.current_state: ScreenState = ScreenState.UNKNOWN
        self.previous_state: ScreenState = ScreenState.UNKNOWN
        self.state_history: List[ScreenSnapshot] = []
        self.max_history_size = 10

        # State detection thresholds
        self.loading_timeout = 30.0  # seconds
        self.interaction_timeout = 5.0  # seconds
        self.element_stability_threshold = 0.8  # 80% element similarity

    def get_current_state(self) -> ScreenState:
        """Get the current screen state.

        Returns:
            Current ScreenState
        """
        return self.current_state

    def detect_screen_state(self) -> ScreenState:
        """Detect the current screen state based on various heuristics.

        Returns:
            Detected ScreenState
        """
        try:
            # Check if screen is loading
            if self._is_screen_loading():
                new_state = ScreenState.LOADING
            # Check if screen is ready for interaction
            elif self._is_screen_ready():
                new_state = ScreenState.READY
            # Check if interaction is in progress
            elif self._is_interaction_in_progress():
                new_state = ScreenState.INTERACTING
            # Check for error states
            elif self._is_error_state():
                new_state = ScreenState.ERROR
            else:
                new_state = ScreenState.UNKNOWN

            # Update state if changed
            if new_state != self.current_state:
                self.previous_state = self.current_state
                self.current_state = new_state
                logger.info(f"Screen state changed: {self.previous_state} -> {self.current_state}")

            return self.current_state

        except Exception as e:
            logger.error(f"Failed to detect screen state: {e}")
            return ScreenState.UNKNOWN

    def take_snapshot(self, include_screenshot: bool = True) -> ScreenSnapshot:
        """Take a snapshot of the current screen state.

        Args:
            include_screenshot: Whether to capture screenshot

        Returns:
            ScreenSnapshot object
        """
        try:
            # Get current elements
            elements = self.element_finder.get_all_elements()

            # Get screenshot if requested
            screenshot_path = None
            if include_screenshot:
                screenshot_path = self.screenshot_capture.capture_screenshot_to_file()

            # Get screen bounds
            screen_bounds = self._get_screen_bounds()

            # Get activity and package info
            activity_name = self._get_current_activity()
            package_name = self._get_current_package()

            # Detect current state
            current_state = self.detect_screen_state()

            # Create metadata
            metadata = {
                'element_count': len(elements),
                'clickable_elements': len([e for e in elements if e.clickable]),
                'visible_elements': len([e for e in elements if e.visible]),
                'screen_size': screen_bounds,
            }

            snapshot = ScreenSnapshot(
                timestamp=time.time(),
                screenshot_path=screenshot_path,
                elements=elements,
                screen_state=current_state,
                activity_name=activity_name,
                package_name=package_name,
                screen_bounds=screen_bounds,
                metadata=metadata
            )

            # Add to history
            self.state_history.append(snapshot)
            if len(self.state_history) > self.max_history_size:
                self.state_history.pop(0)

            logger.debug(f"Took screen snapshot: {len(elements)} elements, state={current_state}")
            return snapshot

        except Exception as e:
            logger.error(f"Failed to take screen snapshot: {e}")
            # Return minimal snapshot
            return ScreenSnapshot(
                timestamp=time.time(),
                screenshot_path=None,
                elements=[],
                screen_state=ScreenState.ERROR,
                activity_name=None,
                package_name=None,
                screen_bounds=(0, 0, 0, 0),
                metadata={'error': str(e)}
            )

    def wait_for_state(self, target_state: ScreenState, timeout: float = 10.0,
                      check_interval: float = 0.5) -> bool:
        """Wait for the screen to reach a specific state.

        Args:
            target_state: Target ScreenState to wait for
            timeout: Maximum time to wait in seconds
            check_interval: How often to check state in seconds

        Returns:
            True if target state reached, False if timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            current_state = self.detect_screen_state()
            if current_state == target_state:
                logger.info(f"Reached target state {target_state} after {time.time() - start_time:.1f}s")
                return True

            time.sleep(check_interval)

        logger.warning(f"Timeout waiting for state {target_state} after {timeout}s")
        return False

    def wait_for_stable_screen(self, stability_duration: float = 2.0,
                              timeout: float = 30.0) -> bool:
        """Wait for the screen to become stable (no major changes).

        Args:
            stability_duration: How long screen must be stable
            timeout: Maximum time to wait

        Returns:
            True if screen stabilized, False if timeout
        """
        start_time = time.time()
        stable_start_time = None

        last_elements = None

        while time.time() - start_time < timeout:
            try:
                current_elements = self.element_finder.get_all_elements()

                if last_elements is not None:
                    similarity = self._calculate_element_similarity(last_elements, current_elements)

                    if similarity >= self.element_stability_threshold:
                        if stable_start_time is None:
                            stable_start_time = time.time()
                        elif time.time() - stable_start_time >= stability_duration:
                            logger.info(f"Screen stabilized after {time.time() - start_time:.1f}s")
                            return True
                    else:
                        stable_start_time = None
                else:
                    stable_start_time = time.time()

                last_elements = current_elements
                time.sleep(0.5)

            except Exception as e:
                logger.warning(f"Error checking screen stability: {e}")
                time.sleep(0.5)

        logger.warning(f"Screen did not stabilize within {timeout}s")
        return False

    def compare_snapshots(self, snapshot1: ScreenSnapshot,
                         snapshot2: ScreenSnapshot) -> Dict[str, Any]:
        """Compare two screen snapshots.

        Args:
            snapshot1: First snapshot
            snapshot2: Second snapshot

        Returns:
            Dictionary with comparison results
        """
        comparison = {
            'time_diff': snapshot2.timestamp - snapshot1.timestamp,
            'state_changed': snapshot1.screen_state != snapshot2.screen_state,
            'element_count_diff': len(snapshot2.elements) - len(snapshot1.elements),
            'activity_changed': snapshot1.activity_name != snapshot2.activity_name,
            'package_changed': snapshot1.package_name != snapshot2.package_name,
        }

        # Calculate element similarity
        if snapshot1.elements and snapshot2.elements:
            comparison['element_similarity'] = self._calculate_element_similarity(
                snapshot1.elements, snapshot2.elements
            )
        else:
            comparison['element_similarity'] = 0.0

        return comparison

    def get_state_history(self) -> List[ScreenSnapshot]:
        """Get the history of screen states.

        Returns:
            List of ScreenSnapshot objects
        """
        return self.state_history.copy()

    def clear_history(self):
        """Clear the state history."""
        self.state_history.clear()
        logger.debug("Cleared screen state history")

    def _is_screen_loading(self) -> bool:
        """Check if screen is in loading state.

        Returns:
            True if screen appears to be loading
        """
        try:
            # Check for loading indicators
            loading_elements = self.element_finder.find_elements_containing_text(
                ['loading', 'please wait', 'progress', 'buffering'], case_sensitive=False
            )

            if loading_elements:
                return True

            # Check for progress bars or spinners
            progress_elements = self.element_finder.find_elements_by_class('android.widget.ProgressBar')
            if progress_elements:
                return True

            # Check if very few elements (might indicate loading)
            all_elements = self.element_finder.get_all_elements()
            if len(all_elements) < 3:
                return True

            return False

        except Exception:
            return False

    def _is_screen_ready(self) -> bool:
        """Check if screen is ready for interaction.

        Returns:
            True if screen appears ready
        """
        try:
            # Check for clickable elements
            clickable_elements = self.element_finder.find_clickable_elements()
            if len(clickable_elements) > 0:
                return True

            # Check for text input fields
            text_fields = self.element_finder.find_elements_by_class('android.widget.EditText')
            if text_fields:
                return True

            # Check for buttons
            buttons = self.element_finder.find_elements_by_class('android.widget.Button')
            if buttons:
                return True

            return False

        except Exception:
            return False

    def _is_interaction_in_progress(self) -> bool:
        """Check if user interaction is currently in progress.

        Returns:
            True if interaction appears to be in progress
        """
        # This is a simple heuristic - in practice, you'd track recent gestures
        # For now, assume no interaction is in progress
        return False

    def _is_error_state(self) -> bool:
        """Check if screen is in an error state.

        Returns:
            True if screen appears to have an error
        """
        try:
            # Check for error messages
            error_elements = self.element_finder.find_elements_containing_text(
                ['error', 'failed', 'sorry', 'problem', 'crash'], case_sensitive=False
            )

            return len(error_elements) > 0

        except Exception:
            return False

    def _get_screen_bounds(self) -> Tuple[int, int, int, int]:
        """Get screen bounds.

        Returns:
            Tuple of (left, top, right, bottom)
        """
        try:
            size = self.driver.get_driver().get_window_size()
            width = size.get('width', 1080)
            height = size.get('height', 1920)
            return (0, 0, width, height)
        except Exception:
            return (0, 0, 1080, 1920)  # Default values

    def _get_current_activity(self) -> Optional[str]:
        """Get current activity name.

        Returns:
            Activity name or None
        """
        try:
            return self.driver.get_driver().current_activity
        except Exception:
            return None

    def _get_current_package(self) -> Optional[str]:
        """Get current package name.

        Returns:
            Package name or None
        """
        try:
            return self.driver.get_driver().current_package
        except Exception:
            return None

    def _calculate_element_similarity(self, elements1: List[UIElement],
                                    elements2: List[UIElement]) -> float:
        """Calculate similarity between two element lists.

        Args:
            elements1: First element list
            elements2: Second element list

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not elements1 and not elements2:
            return 1.0
        if not elements1 or not elements2:
            return 0.0

        # Simple similarity based on bounds overlap
        matches = 0
        total = max(len(elements1), len(elements2))

        for elem1 in elements1:
            for elem2 in elements2:
                if self._elements_similar(elem1, elem2):
                    matches += 1
                    break

        return matches / total

    def _elements_similar(self, elem1: UIElement, elem2: UIElement) -> bool:
        """Check if two elements are similar.

        Args:
            elem1: First element
            elem2: Second element

        Returns:
            True if elements are similar
        """
        # Check bounds similarity (within 10 pixels)
        bounds_diff = (
            abs(elem1.bounds[0] - elem2.bounds[0]),
            abs(elem1.bounds[1] - elem2.bounds[1]),
            abs(elem1.bounds[2] - elem2.bounds[2]),
            abs(elem1.bounds[3] - elem2.bounds[3])
        )

        if all(diff <= 10 for diff in bounds_diff):
            return True

        # Check text similarity
        if elem1.text and elem2.text and elem1.text == elem2.text:
            return True

        # Check class similarity
        if elem1.class_name and elem2.class_name and elem1.class_name == elem2.class_name:
            return True

        return False