"""Crawl controller for pause/resume/stop controls."""

import logging
import threading
from typing import Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class CrawlControlState(Enum):
    """Current state of crawl control."""
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class CrawlController:
    """Thread-safe controller for pause/resume/stop operations during crawl.

    Provides thread-safe flags and event emission for crawl loop control.
    """

    def __init__(self):
        """Initialize the crawl controller."""
        self._lock = threading.Lock()
        self._state = CrawlControlState.STOPPED
        self._state_change_listeners: list[Callable[[CrawlControlState], None]] = []

    @property
    def state(self) -> CrawlControlState:
        """Get the current control state."""
        with self._lock:
            return self._state

    def pause(self) -> None:
        """Pause the crawl.

        If the crawl is running, it will be paused.
        If already paused or stopped, this is a no-op.
        """
        with self._lock:
            if self._state == CrawlControlState.RUNNING:
                self._state = CrawlControlState.PAUSED
                logger.info("Crawl paused")
                self._notify_state_change()

    def resume(self) -> None:
        """Resume a paused crawl.

        If the crawl is paused, it will be resumed.
        If already running or stopped, this is a no-op.
        """
        with self._lock:
            if self._state == CrawlControlState.PAUSED:
                self._state = CrawlControlState.RUNNING
                logger.info("Crawl resumed")
                self._notify_state_change()

    def stop(self) -> None:
        """Stop the crawl.

        Sets the state to STOPPED regardless of current state.
        This is used to initiate graceful shutdown.
        """
        with self._lock:
            if self._state != CrawlControlState.STOPPED:
                self._state = CrawlControlState.STOPPED
                logger.info("Crawl stopped")
                self._notify_state_change()

    def is_running(self) -> bool:
        """Check if the crawl is currently running.

        Returns:
            True if state is RUNNING, False otherwise
        """
        with self._lock:
            return self._state == CrawlControlState.RUNNING

    def is_paused(self) -> bool:
        """Check if the crawl is currently paused.

        Returns:
            True if state is PAUSED, False otherwise
        """
        with self._lock:
            return self._state == CrawlControlState.PAUSED

    def is_stopped(self) -> bool:
        """Check if the crawl is currently stopped.

        Returns:
            True if state is STOPPED, False otherwise
        """
        with self._lock:
            return self._state == CrawlControlState.STOPPED

    def should_continue(self) -> bool:
        """Check if the crawl should continue executing.

        Returns:
            True if state is RUNNING, False if PAUSED or STOPPED
        """
        with self._lock:
            return self._state == CrawlControlState.RUNNING

    def add_state_change_listener(self, listener: Callable[[CrawlControlState], None]) -> None:
        """Add a listener for state changes.

        Args:
            listener: Callable that will be called with the new state
        """
        with self._lock:
            self._state_change_listeners.append(listener)

    def remove_state_change_listener(self, listener: Callable[[CrawlControlState], None]) -> None:
        """Remove a state change listener.

        Args:
            listener: The listener to remove
        """
        with self._lock:
            if listener in self._state_change_listeners:
                self._state_change_listeners.remove(listener)

    def reset(self) -> None:
        """Reset the controller to initial state.

        Sets state back to STOPPED and clears all listeners.
        Useful for starting a new crawl session.
        """
        with self._lock:
            self._state = CrawlControlState.STOPPED
            self._state_change_listeners.clear()
            logger.debug("Crawl controller reset")

    def _notify_state_change(self) -> None:
        """Notify all listeners of a state change.

        Must be called while holding the lock.
        """
        for listener in self._state_change_listeners:
            try:
                listener(self._state)
            except Exception as e:
                logger.error(f"Error in state change listener: {e}")
