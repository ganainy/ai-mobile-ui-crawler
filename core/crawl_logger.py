import logging
import json
import time
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class CrawlLogger:
    """
    Handles logging and reporting for the crawler across multiple channels (Console, DB, UI).
    """
    
    def __init__(self, db_manager, config):
        self.db_manager = db_manager
        self.config = config

    def log_ui_step(self, step_count: int):
        """Log current step to the UI."""
        print(f"UI_STEP:{step_count}", flush=True)
        print(f"STEP: {step_count}")
        logger.info(f"Starting step {step_count}")

    def log_ai_context(self, step_count: int, is_stuck: bool, stuck_reason: str, 
                        action_history: List[Dict[str, Any]], 
                        visited_screens: List[Dict[str, Any]], 
                        current_screen_id: Optional[int], 
                        current_screen_visit_count: int, 
                        current_screen_actions: List[Dict[str, Any]]):
        """Log the context being sent to the AI (compact version)."""
        # Log a compact summary instead of verbose details
        context_summary = (
            f"Step {step_count} | Screen #{current_screen_id} "
            f"(visit #{current_screen_visit_count}) | "
            f"History: {len(action_history)} actions | "
            f"Screens: {len(visited_screens)}"
        )
        
        if is_stuck:
            logger.warning(f"⚠️ STUCK: {stuck_reason}")
        
        logger.info(context_summary)

    def log_ai_decision(self, action_data: Dict[str, Any], decision_time: float):
        """Log the AI's decision."""
        action_str = f"{action_data.get('action', 'unknown')} on {action_data.get('target_identifier', 'unknown')}"
        reasoning = action_data.get('reasoning', '')
        
        print(f"UI_ACTION: {action_str}", flush=True)
        print(f"ACTION: {action_str}")
        if reasoning:
            print(f"REASONING: {reasoning}")
        print(f"AI_DECISION_TIME: {decision_time:.3f}s")
        
        logger.info(f"AI decided: {action_str}")
        if reasoning:
            logger.info(f"AI reasoning: {reasoning}")
        logger.info(f"AI decision time: {decision_time:.3f}s")
        return action_str

    def log_step_to_db(self, run_id: int, step_number: int, from_screen_id: Optional[int], 
                        to_screen_id: Optional[int], action_data: Optional[Dict[str, Any]], 
                        action_str: str, success: bool, ai_response_time_ms: float, 
                        token_count: Optional[int], ai_input_prompt: Optional[str], 
                        element_find_time_ms: Optional[float], error_message: Optional[str] = None):
        """Log a step to the database."""
        if not self.db_manager or not run_id:
            return

        try:
            ai_suggestion_json = json.dumps(action_data) if action_data else None
            mapped_action_json = json.dumps(action_data) if action_data else None
            
            if not success and not error_message:
                error_message = "Action execution failed"
                
            self.db_manager.insert_step_log(
                run_id=run_id,
                step_number=step_number,
                from_screen_id=from_screen_id,
                to_screen_id=to_screen_id,
                action_description=action_str,
                ai_suggestion_json=ai_suggestion_json,
                mapped_action_json=mapped_action_json,
                execution_success=success,
                error_message=error_message,
                ai_response_time=ai_response_time_ms,
                total_tokens=token_count if token_count else None,
                ai_input_prompt=ai_input_prompt,
                element_find_time_ms=element_find_time_ms
            )
            logger.debug(f"Logged step {step_number} to database")
        except Exception as e:
            logger.error(f"Error logging step to database: {e}", exc_info=True)

    def _get_transition_message(self, from_id: Optional[int], to_id: Optional[int]) -> str:
        """Generate transition message between screens."""
        if to_id:
            if from_id == to_id:
                return " → stayed on same screen"
            else:
                return f" → navigated to Screen #{to_id}"
        return " → no navigation"
