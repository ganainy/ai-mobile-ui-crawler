"""Screen state management for mobile applications."""

import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from mobile_crawler.infrastructure.appium_driver import AppiumDriver
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
    screen_state: ScreenState
    activity_name: Optional[str]
    package_name: Optional[str]
    screen_bounds: Tuple[int, int, int, int]  # left, top, right, bottom
    metadata: Dict[str, Any]


class ScreenStateManager:
    """
    Manages screen state detection and transitions.
    """

    def __init__(self, appium_driver: AppiumDriver,
                 screenshot_capture: Optional[ScreenshotCapture] = None):
        """Initialize screen state manager.

        Args:
            appium_driver: AppiumDriver instance
            screenshot_capture: ScreenshotCapture instance (optional)
        """
        self.driver = appium_driver
        self.screenshot_capture = screenshot_capture or ScreenshotCapture(appium_driver)

        self.current_state: ScreenState = ScreenState.UNKNOWN
        self.previous_state: ScreenState = ScreenState.UNKNOWN
        self.state_history: List[ScreenSnapshot] = []
        self.max_history_size = 10

        # State detection thresholds
        self.loading_timeout = 30.0  # seconds
        self.interaction_timeout = 5.0  # seconds
        self.element_stability_threshold = 0.8  # Using same threshold name for image similarity

    def get_current_state(self) -> ScreenState:
        """Get the current screen state.

        Returns:
            Current ScreenState
        """
        return self.current_state

    def detect_screen_state(self) -> ScreenState:
        """Detect the current screen state.
        
        In Image-Only mode, this primarily defaults to READY unless there is a
        system-level indication otherwise, delegating visual state detection
        to the VLM.
        
        Returns:
            Detected ScreenState
        """
        try:
            # Default to READY in image-only mode
            new_state = ScreenState.READY

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
                'screen_size': screen_bounds,
                'image_only_mode': True
            }

            snapshot = ScreenSnapshot(
                timestamp=time.time(),
                screenshot_path=screenshot_path,
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

            logger.debug(f"Took screen snapshot: state={current_state}")
            return snapshot

        except Exception as e:
            logger.error(f"Failed to take screen snapshot: {e}")
            # Return minimal snapshot
            return ScreenSnapshot(
                timestamp=time.time(),
                screenshot_path=None,
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
        last_screenshot = None

        while time.time() - start_time < timeout:
            try:
                # Take screenshot for comparison
                current_screenshot = self.screenshot_capture.capture_screenshot_to_file()
                
                if last_screenshot is not None:
                    # Compare screenshots using image hash
                    similarity = self._calculate_screenshot_similarity(last_screenshot, current_screenshot)
                    
                    if similarity >= self.element_stability_threshold:
                        if stable_start_time is None:
                            stable_start_time = time.time()
                        elif time.time() - stable_start_time >= stability_duration:
                            logger.info(f"Screen stabilized after {time.time() - start_time:.1f}s (image-only mode)")
                            return True
                    else:
                        stable_start_time = None
                else:
                    stable_start_time = time.time()
                
                last_screenshot = current_screenshot
                time.sleep(0.5)

            except Exception as e:
                logger.warning(f"Error checking screen stability: {e}")
                time.sleep(0.5)

        logger.warning(f"Screen did not stabilize within {timeout}s")
        return False

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

    def _calculate_screenshot_similarity(self, screenshot1: str, screenshot2: str) -> float:
        """Calculate similarity between two screenshots using image hash.
        
        Args:
            screenshot1: Path to first screenshot
            screenshot2: Path to second screenshot
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        try:
            from PIL import Image
            import imagehash
            
            # Load images
            img1 = Image.open(screenshot1)
            img2 = Image.open(screenshot2)
            
            # Calculate perceptual hash
            hash1 = imagehash.phash(img1)
            hash2 = imagehash.phash(img2)
            
            # Calculate similarity (hamming distance)
            # Lower hamming distance = more similar
            max_distance = hash1.hash.size * hash1.hash.size
            hamming_distance = hash1 - hash2
            
            similarity = 1.0 - (hamming_distance / max_distance)
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            logger.debug(f"Failed to calculate screenshot similarity: {e}")
            return 0.0