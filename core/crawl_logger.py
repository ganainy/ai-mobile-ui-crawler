import logging
import json
import time
from typing import List, Dict, Any, Optional, Union

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
        

    def log_ai_input_prompt(self, ai_input_prompt: Optional[Union[str, Dict[str, Any]]]):
        """Log the complete AI input prompt to the UI."""
        if ai_input_prompt:
            if isinstance(ai_input_prompt, dict):
                # Send structured data to UI
                try:
                    prompt_json = json.dumps(ai_input_prompt)
                    print(f"UI_AI_PROMPT:{prompt_json}", flush=True)
                except Exception:
                     # Fallback
                     print(f"UI_AI_PROMPT:{ai_input_prompt.get('full_prompt', str(ai_input_prompt))}", flush=True)
            else:
                print(f"UI_AI_PROMPT:{ai_input_prompt}", flush=True)

    def _resolve_target_to_text(self, target_identifier: Optional[str], ocr_results: Optional[List[Dict[str, Any]]]) -> str:
        """Resolve target identifier to human-readable text.
        
        For OCR IDs like 'ocr_8', returns the actual text content (e.g., 'Login').
        For XML IDs, returns the ID itself.
        """
        if not target_identifier:
            return "unknown"
        
        # Check if it's an OCR ID (format: ocr_X)
        if target_identifier.startswith("ocr_") and ocr_results:
            try:
                idx = int(target_identifier.split("_")[1])
                if 0 <= idx < len(ocr_results):
                    text = ocr_results[idx].get('text', target_identifier)
                    # Truncate long text
                    if len(text) > 30:
                        text = text[:27] + "..."
                    return f"'{text}'"
            except (ValueError, IndexError):
                pass
        
        # Return the ID itself for XML identifiers
        return target_identifier

    def log_ai_decision(self, action_data: Dict[str, Any], decision_time: float, 
                        ai_input_prompt: Optional[Union[str, Dict[str, Any]]] = None,
                        ocr_results: Optional[List[Dict[str, Any]]] = None):
        """Log the AI's decision.
        
        Args:
            action_data: The AI's decision including action, target, reasoning
            decision_time: Time taken for AI to make decision
            ai_input_prompt: The prompt sent to AI (for inspector)
            ocr_results: OCR results from current screen (to resolve ocr_X to text)
        """
        # Log the AI input prompt first (before the action)
        if ai_input_prompt:
            self.log_ai_input_prompt(ai_input_prompt)
        
        # Log the full AI response for the inspector
        try:
            # Inject meta-data for the UI
            ui_data = action_data.copy()
            ui_data['_meta'] = {
                'decision_time_sec': round(decision_time, 3)
            }
            response_json = json.dumps(ui_data, indent=2)
            print(f"UI_AI_RESPONSE:{response_json}", flush=True)
        except Exception:
            pass
        
        # Resolve target to human-readable text
        target = action_data.get('target_identifier', 'unknown')
        readable_target = self._resolve_target_to_text(target, ocr_results)
        
        action_str = f"{action_data.get('action', 'unknown')} on {readable_target}"
        reasoning = action_data.get('reasoning', '')
        
        print(f"UI_ACTION: {action_str}", flush=True)
        print(f"ACTION: {action_str}")
        if reasoning:
            print(f"REASONING: {reasoning}")
        print(f"AI_DECISION_TIME: {decision_time:.3f}s")
        
        if reasoning:
            pass
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
                ai_input_prompt=ai_input_prompt.get('full_prompt', str(ai_input_prompt)) if isinstance(ai_input_prompt, dict) else ai_input_prompt,
                element_find_time_ms=element_find_time_ms
            )
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
