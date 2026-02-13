"""Exploration journal for tracking crawl history."""

import json
import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class JournalEntry:
    """Represents a single journal entry from exploration history."""

    step_number: int
    from_screen_id: Optional[int]
    to_screen_id: Optional[int]
    action_type: str
    action_description: Optional[str]
    success: bool
    error_message: Optional[str]
    timestamp: str
    target_element: Optional[str] = None


class ExplorationJournal:
    """Manages exploration journal entries for AI context."""

    def __init__(self, step_log_repository):
        """Initialize the exploration journal.

        Args:
            step_log_repository: Repository for accessing step logs
        """
        self._step_log_repository = step_log_repository

    def get_entries(self, run_id: int, limit: int = 15) -> List[JournalEntry]:
        """Get exploration journal entries for a run.

        Args:
            run_id: ID of the run to get entries for
            limit: Maximum number of entries to return (default: 15)

        Returns:
            List of JournalEntry objects, ordered by step number (most recent last)
        """
        try:
            # Query step logs from repository
            step_logs = self._step_log_repository.get_exploration_journal(
                run_id=run_id,
                limit=limit
            )

            # Convert to JournalEntry objects
            entries = []
            for log in step_logs:
                # Extract target element from target_bbox_json if available
                target_element = None
                if log.target_bbox_json:
                    try:
                        target_info = json.loads(log.target_bbox_json)
                        if isinstance(target_info, dict):
                            # Try to get 'id' first, then 'text', then 'class'
                            target_element = (
                                target_info.get('id') or
                                target_info.get('text') or
                                target_info.get('class')
                            )
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        pass

                entry = JournalEntry(
                    step_number=log.step_number,
                    from_screen_id=log.from_screen_id,
                    to_screen_id=log.to_screen_id,
                    action_type=log.action_type,
                    action_description=log.action_description,
                    success=log.execution_success,
                    error_message=log.error_message,
                    timestamp=log.timestamp.isoformat() if log.timestamp else None,
                    target_element=target_element
                )
                entries.append(entry)

            logger.debug(f"Retrieved {len(entries)} journal entries for run {run_id}")
            return entries

        except Exception as e:
            logger.error(f"Failed to retrieve exploration journal for run {run_id}: {e}")
            return []

    def get_formatted_entries(self, run_id: int, limit: int = 15) -> str:
        """Get exploration journal entries formatted for AI prompt.

        Args:
            run_id: ID of the run to get entries for
            limit: Maximum number of entries to return (default: 15)

        Returns:
            Formatted string of journal entries for AI context
        """
        entries = self.get_entries(run_id, limit)

        if not entries:
            return "No exploration history available."

        lines = []
        for entry in entries:
            action_desc = entry.action_type

            # Add target element if available
            if entry.target_element:
                action_desc += f" on {entry.target_element}"

            # Add action description if available
            if entry.action_description:
                action_desc += f" ({entry.action_description})"

            status = "✓" if entry.success else "✗"
            if entry.error_message:
                status += f" ({entry.error_message})"

            line = f"Step {entry.step_number}: {action_desc} - {status}"
            lines.append(line)

        return "\n".join(lines)
