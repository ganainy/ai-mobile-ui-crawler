"""State transition graph and layout hashing for AI crawler navigation."""

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("crawler_agent")


class StateGraphTracker:
    """Tracks unique UI states using layout XML hashes and maintains a transition graph (FSM)."""

    def __init__(self, run_id: int, logs_dir: str | Path | None = None):
        """Initialize the state graph tracker.

        Args:
            run_id: The ID of the crawler run.
            logs_dir: Optional directory to persist the state graph JSON.
        """
        self.run_id = run_id
        self.logs_dir = Path(logs_dir) if logs_dir else None

        # Maps state_hash -> dict with state details (e.g., first_seen_step, package, activity)
        self.states: dict[str, dict[str, Any]] = {}

        # List of transitions: dict with keys (from_state, to_state, action, step)
        self.transitions: list[dict[str, Any]] = []

        # Path of hashes visited in the current run, in order
        self.history: list[str] = []

        # Set up dynamic content regex patterns to filter out
        self.time_pattern = re.compile(r"^\d{1,2}:\d{2}\s*(?:AM|PM)?$", re.IGNORECASE)
        self.battery_pattern = re.compile(r"^\d{1,3}%\s*$", re.IGNORECASE)
        self.date_pattern = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$")

    def filter_dynamic_element(self, element: dict[str, Any]) -> bool:
        """Determine if an element represents dynamic system UI or temporary state.

        Args:
            element: Formatted UI element dictionary.

        Returns:
            True if the element is dynamic and should be filtered out from hashing.
        """
        resource_id = element.get("resourceId", "") or ""
        class_name = element.get("className", "") or ""
        text = element.get("text", "") or ""

        # Filter out status bar, navigation bar, and battery/system indicators
        system_keywords = ["statusBar", "status_bar", "navigationBar", "nav_bar", "battery", "wifi", "signal"]
        if any(kw.lower() in resource_id.lower() for kw in system_keywords):
            return True
        if any(kw.lower() in class_name.lower() for kw in system_keywords):
            return True

        # Filter out elements matching dynamic value patterns
        text_str = str(text).strip()
        if self.time_pattern.match(text_str):
            return True
        if self.battery_pattern.match(text_str):
            return True
        if self.date_pattern.match(text_str):
            return True

        return False

    def compute_layout_hash(self, elements: list[dict[str, Any]]) -> str:
        """Compute a SHA-256 hash representing the structural layout of the screen.

        Filters out dynamic elements and hashes only the stable structural properties
        (className, resourceId, bounds, and non-dynamic text) of the UI elements.

        Args:
            elements: List of formatted UI elements.

        Returns:
            SHA-256 hex string hash of the screen state.
        """
        if not elements:
            return hashlib.sha256(b"empty_state").hexdigest()

        stable_elements = []
        for el in elements:
            if self.filter_dynamic_element(el):
                continue

            # Extract stable features
            stable_node = {
                "className": el.get("className", ""),
                "resourceId": el.get("resourceId", ""),
                "bounds": el.get("bounds", ""),
                # Keep text only if it does not look like dynamic time/date values
                "text": el.get("text", "") if el.get("text") else "",
                "checkedState": el.get("checkedState", "")
            }
            stable_elements.append(stable_node)

        # Sort stable elements by bounds/index to guarantee deterministic ordering
        stable_elements.sort(key=lambda x: (x["bounds"], x["resourceId"], x["className"]))

        # Serialize to JSON with sorted keys
        canonical_str = json.dumps(stable_elements, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def record_state(self, state_hash: str, step_number: int, package: str, activity: str) -> bool:
        """Record a visited state.

        Args:
            state_hash: Computed layout hash of the screen.
            step_number: Current crawl step number.
            package: Android app package name.
            activity: Current Android activity name.

        Returns:
            True if this is a newly discovered state, False if revisited.
        """
        self.history.append(state_hash)

        if state_hash not in self.states:
            self.states[state_hash] = {
                "first_seen_step": step_number,
                "visit_count": 1,
                "package": package,
                "activity": activity,
                "last_seen_step": step_number
            }
            logger.debug(f"StateGraph: Discovered new screen state: {state_hash[:8]} (Step {step_number})")
            return True
        else:
            self.states[state_hash]["visit_count"] += 1
            self.states[state_hash]["last_seen_step"] = step_number
            logger.debug(
                f"StateGraph: Revisited screen state: {state_hash[:8]} "
                f"(Visits: {self.states[state_hash]['visit_count']})"
            )
            return False

    def record_transition(self, from_hash: str, to_hash: str, action: dict[str, Any] | str, step_number: int) -> None:
        """Record a navigation transition between two states.

        Args:
            from_hash: The starting state's layout hash.
            to_hash: The destination state's layout hash.
            action: Description or dictionary representation of the action taken.
            step_number: Current crawl step number.
        """
        # Simplify action representation if it is a dictionary
        action_desc = action
        if isinstance(action, dict):
            action_type = action.get("action", "unknown")
            target = action.get("label_id") or action.get("target_bounding_box") or ""
            action_desc = f"{action_type}({target})"

        self.transitions.append({
            "from_state": from_hash,
            "to_state": to_hash,
            "action": str(action_desc),
            "step": step_number
        })
        logger.debug(f"StateGraph: Recorded transition {from_hash[:8]} --[{action_desc}]--> {to_hash[:8]}")

    def detect_loop(self, window_size: int = 4) -> bool:
        """Detect if the crawler is stuck in a navigation loop.

        Args:
            window_size: Number of steps back to check for repetition.

        Returns:
            True if a loop is detected.
        """
        if len(self.history) < window_size * 2:
            return False

        # Look for repeating sub-sequences in the history
        recent_states = self.history[-window_size:]
        previous_states = self.history[-window_size*2:-window_size]

        if recent_states == previous_states:
            logger.warning(f"StateGraph: Loop detected in recent history: {[s[:8] for s in recent_states]}")
            return True

        return False

    def get_loop_recovery_hint(self, current_hash: str, available_elements: list[dict[str, Any]]) -> str | None:
        """Provide a hint/action suggestion to escape a detected loop.

        Args:
            current_hash: Current screen hash.
            available_elements: Currently clickable elements.

        Returns:
            Advice string or None.
        """
        # Find all transitions originating from the current state
        attempted_actions = [
            t["action"] for t in self.transitions if t["from_state"] == current_hash
        ]

        # Check if there are clickable elements we haven't interacted with in this state yet
        unexplored_buttons = []
        for el in available_elements:
            if not el.get("clickable", True):
                continue

            # Approximate action signatures
            index = el.get("index")
            text = el.get("text", "")
            resource_id = el.get("resourceId", "")

            # Simple heuristic match to see if we clicked it
            signature = f"click({index})"
            has_clicked = any(
                signature in a or
                (text and text in a) or
                (resource_id and resource_id in a)
                for a in attempted_actions
            )

            if not has_clicked:
                unexplored_buttons.append(el)

        if unexplored_buttons:
            first_unexplored = unexplored_buttons[0]
            label = first_unexplored.get("index") or first_unexplored.get("text") or first_unexplored.get("resourceId")
            return f"Loop warning! You are stuck in a loop. Try interacting with a new, unexplored element: element [{label}]."

        return "Loop warning! You are stuck in a loop. Try using the 'back' button or scrolling to escape the loop."

    def save(self) -> None:
        """Save the transition graph and states as a JSON file in the logs directory."""
        if not self.logs_dir:
            return

        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.logs_dir / "state_graph.json"

            graph_data = {
                "run_id": self.run_id,
                "unique_states_count": len(self.states),
                "total_transitions": len(self.transitions),
                "states": self.states,
                "transitions": self.transitions,
                "history": self.history
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(graph_data, f, indent=2, ensure_ascii=True)
            logger.info(f"StateGraph saved successfully to {output_path}")
        except Exception as e:
            logger.warning(f"Failed to save StateGraph: {e}")
