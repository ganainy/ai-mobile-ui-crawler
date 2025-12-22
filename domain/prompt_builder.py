"""
Prompt building and processing module for the AI agent.

Handles context-aware prompt construction, static/dynamic prompt parts,
and LangChain Runnable chain creation for action decisions.
"""
import json
import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.runnables import RunnableLambda
from domain.prompts import JSON_OUTPUT_SCHEMA, get_available_actions
from utils.utils import parse_json_robust, repair_json_string
from config.numeric_constants import EXPLORATION_JOURNAL_MAX_LENGTH_DEFAULT

logger = logging.getLogger(__name__)


class ActionDecisionChain:
    """
    Wrapper for the LangChain runnable that handles execution and response parsing.
    """
    def __init__(self, chain):
        self.chain = chain

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run the decision chain with the given context."""
        try:
            # The chain expects a dict with prompt variables
            # Format the context for the prompt template
            result = self.chain.invoke(context)
            # If result is a string, try to parse as JSON
            if isinstance(result, str):
                return self.parse_json(result)
            return result if isinstance(result, dict) else {}
        except Exception as e:
            logger.error(f"Error running ActionDecisionChain: {e}", exc_info=True)
            return {}

    def parse_json(self, text: str) -> Dict[str, Any]:
        """Robust JSON parsing with fallback and repair."""
        result = parse_json_robust(text)
        if not result:
            from config.numeric_constants import RESULT_TRUNCATION_LENGTH
            logger.warning(f"Could not parse JSON from result: {text[:RESULT_TRUNCATION_LENGTH]}")
        return result


class PromptBuilder:
    """
    Handles construction of complex prompts for the mobile app UI testing agent.
    
    Manages static prompt parts (schemas, available actions) and dynamic context
    (screen XML, action history, stuck detection) to build effective LLM inputs.
    """
    
    def __init__(self, config):
        """
        Initialize the PromptBuilder.
        
        Args:
            config: Application configuration
        """
        self.cfg = config
        self._static_prompt_logged = False
    
    def create_prompt_chain(self, prompt_template: str, llm_wrapper, ai_interaction_readable_logger=None):
        """
        Create a LangChain Runnable chain from a prompt template.
        
        Args:
            prompt_template: The prompt template string with placeholders
            llm_wrapper: The LLM Runnable wrapper
            ai_interaction_readable_logger: Optional logger for human-readable prompt logging
            
        Returns:
            A Runnable chain: PromptTemplate | LLM | OutputParser
        """
        # Format the template with static values
        # Get available actions from config property (reads from database or defaults)
        available_actions = get_available_actions(self.cfg)
        action_list_str = "\n".join([f"- {action}: {desc}" for action, desc in available_actions.items()])
        json_output_guidance = json.dumps(JSON_OUTPUT_SCHEMA, indent=2)
        
        # Get journal max length from config or use default
        journal_max_length = self.cfg.get('EXPLORATION_JOURNAL_MAX_LENGTH', EXPLORATION_JOURNAL_MAX_LENGTH_DEFAULT)
        
        # Create formatted prompt string
        formatted_prompt = prompt_template.format(
            json_schema=json_output_guidance,
            action_list=action_list_str,
            journal_max_length=journal_max_length
        )
        
        # Log static prompt parts once
        if ai_interaction_readable_logger and not self._static_prompt_logged:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._static_prompt_logged = True
            
        def format_prompt_wrapper(context: Dict[str, Any]) -> str:
            """Wrapper to call self.format_prompt with static part."""
            return self.format_prompt(prompt_template, context, static_prompt_part=formatted_prompt)
            
        def parse_json_output(llm_output: str) -> Dict[str, Any]:
            """Parse JSON from LLM output."""
            try:
                result = parse_json_robust(llm_output)
                if not result:
                    logger.warning(f"Could not parse JSON from LLM output: {llm_output[:200]}")
                return result
            except Exception as e:
                logger.error(f"Error in parse_json_output: {e}")
                return {}
        
        # Create chain: format prompt -> LLM -> parse JSON
        chain = RunnableLambda(format_prompt_wrapper) | llm_wrapper | RunnableLambda(parse_json_output)
        return chain

    def format_prompt(self, prompt_template: str, context: Dict[str, Any], static_prompt_part: str = None) -> str:
        """
        Format the prompt with context variables.
        
        Args:
            prompt_template: The raw template string (unused if static_prompt_part is provided)
            context: Dictionary containing dynamic context data
            static_prompt_part: Optional pre-formatted static part. If None, it will be generated.
            
        Returns:
            Complete formatted prompt string
        """
        # Generate static part if not provided
        formatted_prompt = static_prompt_part
        if formatted_prompt is None:
            available_actions = get_available_actions(self.cfg)
            # Override available actions if provided in context (for preview)
            if context.get('available_actions'):
                available_actions = context['available_actions']
                
            action_list_str = "\n".join([f"- {action}: {desc}" for action, desc in available_actions.items()])
            json_output_guidance = json.dumps(JSON_OUTPUT_SCHEMA, indent=2)
            
            # Get journal max length from config or use default
            journal_max_length = self.cfg.get('EXPLORATION_JOURNAL_MAX_LENGTH', EXPLORATION_JOURNAL_MAX_LENGTH_DEFAULT)
            
            try:
                formatted_prompt = prompt_template.format(
                    json_schema=json_output_guidance,
                    action_list=action_list_str,
                    journal_max_length=journal_max_length
                )
            except Exception as e:
                # Fallback if specific keys are missing in custom template
                logger.warning(f"Error formatting prompt template: {e}")
                formatted_prompt = prompt_template
        
        # Build the full prompt with context
        prompt_parts = [formatted_prompt]
        
        # Build dynamic parts separately for logging
        dynamic_parts = []
        
        # Add context information
        xml_included = False
        if context.get("xml_context"):
            xml_string = context['xml_context']
            if not isinstance(xml_string, str):
                xml_string = str(xml_string)
            
            xml_part = f"\n\nCurrent screen XML:\n{xml_string}"
            prompt_parts.append(xml_part)
            dynamic_parts.append(xml_part)
            xml_included = True

        # Add OCR context if available
        if context.get("ocr_context"):
            ocr_items = context['ocr_context']
            if ocr_items:
                ocr_lines = ["\n\nVisual Elements (OCR detected):"]
                ocr_lines.append("IMPORTANT: Use 'ocr_X' IDs as target_identifier for actions.")
                ocr_lines.append("BUT in your exploration_journal, write the ACTUAL TEXT for clarity.")
                ocr_lines.append("Example: Instead of 'CLICKED ocr_3' write 'CLICKED \"Login\" button (ocr_3)'")
                ocr_lines.append("")
                for idx, item in enumerate(ocr_items):
                    text = item.get('text', '').strip()
                    # Assign a temporary ID based on index
                    elem_id = f"ocr_{idx}"
                    # Include bounds as a hint, though LLM should rely on ID
                    bounds = item.get('bounds')
                    ocr_lines.append(f"- ID: {elem_id} | Text: \"{text}\" | Bounds: {bounds}")
                
                ocr_part = "\n".join(ocr_lines)
                prompt_parts.append(ocr_part)
                dynamic_parts.append(ocr_part)
        
        # Add stuck detection warning if applicable
        if context.get("is_stuck"):
            stuck_reason = context.get("stuck_reason", "Multiple actions on same screen")
            current_screen_actions = context.get('current_screen_actions', [])
            current_screen_id = context.get('current_screen_id')
            
            forbidden_actions = []
            for action in current_screen_actions:
                action_desc = action.get('action_description', '')
                success = action.get('execution_success', False)
                to_screen_id = action.get('to_screen_id')
                
                if success and (to_screen_id == current_screen_id or to_screen_id is None):
                    forbidden_actions.append(action_desc)
            
            forbidden_text = ""
            if forbidden_actions:
                forbidden_lines = ["FORBIDDEN (these kept you here):"]
                for action in forbidden_actions:
                    forbidden_lines.append(f"  - {action}")
                forbidden_text = "\n".join(forbidden_lines)
            
            stuck_warning = f"""
** STUCK: {stuck_reason} **
You must escape this screen. DO NOT repeat actions that kept you here.
{forbidden_text}

ESCAPE OPTIONS:
1. Use "back" action to return to previous screen
2. Click navigation elements: skipButton, ctaButton, toolbarBackIcon, nav tabs
3. Scroll only if you haven't scrolled yet

State in reasoning: "I am escaping by..."
"""
            prompt_parts.append(stuck_warning)
            dynamic_parts.append(stuck_warning)
        
        # Add exploration journal
        exploration_journal = context.get("exploration_journal", "")
        if exploration_journal:
            journal_part = f"\n\nExploration Journal (your action history):\n{exploration_journal}"
            prompt_parts.append(journal_part)
            dynamic_parts.append(journal_part)
        else:
            # First step - no journal yet
            journal_hint = "\n\nExploration Journal: Empty (first action - describe initial screen state)"
            prompt_parts.append(journal_hint)
            dynamic_parts.append(journal_hint)
        
        # Add actions already tried on current screen (lightweight, always shown)
        current_screen_actions = context.get("current_screen_actions", [])
        if current_screen_actions:
            current_screen_id = context.get('current_screen_id')
            actions_tried_lines = [f"\n\nActions Tried on This Screen (#{current_screen_id}):"]
            for action in current_screen_actions[-8:]:  # Last 8 actions on this screen
                action_desc = action.get('action_description', 'unknown action')
                success = action.get('execution_success', False)
                to_screen_id = action.get('to_screen_id')
                
                if success:
                    if to_screen_id and to_screen_id != current_screen_id:
                        result = f"-> screen #{to_screen_id}"
                    else:
                        result = "-> stayed (ineffective)"
                else:
                    result = "-> FAILED"
                
                actions_tried_lines.append(f"  - {action_desc} {result}")
            
            actions_tried_lines.append("Choose something NOT in this list.")
            actions_tried_part = "\n".join(actions_tried_lines)
            prompt_parts.append(actions_tried_part)
            dynamic_parts.append(actions_tried_part)
        
        # Add last action outcome - this is CRITICAL for AI to learn what actually happened
        if context.get("last_action_feedback"):
            feedback = context['last_action_feedback']
            # Make the feedback very prominent
            feedback_part = f"""

=== LAST ACTION OUTCOME ===
{feedback}

IMPORTANT: Use this outcome to update your exploration_journal accurately.
- If it says "STAYED on same screen" -> that action was ineffective, DO NOT repeat it
- If it says "NAVIGATED to new screen" -> record the transition in your journal
==========================="""
            prompt_parts.append(feedback_part)
            dynamic_parts.append(feedback_part)
        

        
        if context.get("current_screen_visit_count"):
            visit_count_part = f"\n\nScreen visit count: {context['current_screen_visit_count']}"
            prompt_parts.append(visit_count_part)
            dynamic_parts.append(visit_count_part)

        # Inject Test Credentials if available in Config
        # These are critical for login flows
        test_email = self.cfg.get("TEST_EMAIL")
        test_password = self.cfg.get("TEST_PASSWORD")
        test_name = self.cfg.get("TEST_NAME")
        
        if test_email or test_password or test_name:
            credential_lines = ["\n\nUSER-PROVIDED TEST CREDENTIALS:"]
            credential_lines.append("Use these details if you need to Sign Up, Log In, or fill forms:")
            if test_name:
                credential_lines.append(f"- Name: {test_name}")
            if test_email:
                credential_lines.append(f"- Email: {test_email}")
            if test_password:
                credential_lines.append(f"- Password: {test_password}")
            
            creds_part = "\n".join(credential_lines)
            prompt_parts.append(creds_part)
            # Note: We add to dynamic parts too so it's logged/debuggable
            dynamic_parts.append(creds_part)
        
        closing_part = "\n\nPlease respond with a JSON object matching the schema above."
        prompt_parts.append(closing_part)
        dynamic_parts.append(closing_part)
        
        # Store dynamic parts in context for logging
        context['_dynamic_prompt_parts'] = "\n".join(dynamic_parts)
        context['_static_prompt_part'] = formatted_prompt
        
        # Store the full prompt in context for database storage
        full_prompt = "\n".join(prompt_parts)
        context['_full_ai_input_prompt'] = full_prompt
        
        return full_prompt
