"""Repository for managing AI interactions in crawler.db."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from mobile_crawler.infrastructure.database import DatabaseManager


@dataclass
class AIInteraction:
    """Data class representing an AI interaction."""
    id: Optional[int]
    run_id: int
    step_number: int
    timestamp: datetime
    
    # Request Details
    request_json: str
    screenshot_path: Optional[str]
    
    # Response Details
    response_raw: Optional[str]
    response_parsed_json: Optional[str]
    
    # Performance Metrics
    tokens_input: Optional[int]
    tokens_output: Optional[int]
    latency_ms: Optional[float]
    
    # Status
    success: bool
    error_message: Optional[str]
    retry_count: int


class AIInteractionRepository:
    """Repository for CRUD operations on ai_interactions table."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository with database manager.

        Args:
            db_manager: DatabaseManager instance for crawler.db
        """
        self.db_manager = db_manager

    def create_ai_interaction(self, interaction: AIInteraction) -> int:
        """Create a new AI interaction and return its ID.

        Args:
            interaction: AIInteraction object (id will be ignored)

        Returns:
            The ID of the newly created AI interaction
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ai_interactions (
                run_id, step_number, timestamp, request_json, screenshot_path,
                response_raw, response_parsed_json, tokens_input, tokens_output,
                latency_ms, success, error_message, retry_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            interaction.run_id,
            interaction.step_number,
            interaction.timestamp.isoformat(),
            interaction.request_json,
            interaction.screenshot_path,
            interaction.response_raw,
            interaction.response_parsed_json,
            interaction.tokens_input,
            interaction.tokens_output,
            interaction.latency_ms,
            interaction.success,
            interaction.error_message,
            interaction.retry_count
        ))

        conn.commit()
        return cursor.lastrowid

    def get_ai_interactions_by_run(self, run_id: int) -> list[AIInteraction]:
        """Get all AI interactions for a run.

        Args:
            run_id: The run ID to get interactions for

        Returns:
            List of AIInteraction objects for the run
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, run_id, step_number, timestamp, request_json, screenshot_path,
                   response_raw, response_parsed_json, tokens_input, tokens_output,
                   latency_ms, success, error_message, retry_count
            FROM ai_interactions
            WHERE run_id = ?
            ORDER BY step_number
        """, (run_id,))

        interactions = []
        for row in cursor.fetchall():
            interactions.append(AIInteraction(
                id=row[0],
                run_id=row[1],
                step_number=row[2],
                timestamp=datetime.fromisoformat(row[3]),
                request_json=row[4],
                screenshot_path=row[5],
                response_raw=row[6],
                response_parsed_json=row[7],
                tokens_input=row[8],
                tokens_output=row[9],
                latency_ms=row[10],
                success=bool(row[11]),
                error_message=row[12],
                retry_count=row[13]
            ))

        return interactions