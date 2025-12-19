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
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    # Try to extract JSON from text if wrapped
                    json_match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
                    from config.numeric_constants import RESULT_TRUNCATION_LENGTH
                    logger.warning(f"Could not parse JSON from chain result: {result[:RESULT_TRUNCATION_LENGTH]}")
                    return {}
            return result if isinstance(result, dict) else {}
        except Exception as e:
            logger.error(f"Error running ActionDecisionChain: {e}", exc_info=True)
            return {}


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
        
        # Create formatted prompt string
        formatted_prompt = prompt_template.format(
            json_schema=json_output_guidance,
            action_list=action_list_str
        )
        
        # Log static prompt parts once
        if ai_interaction_readable_logger and not self._static_prompt_logged:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ai_interaction_readable_logger.info("=" * 80)
            ai_interaction_readable_logger.info(f"AI PROMPT CONFIGURATION - {timestamp}")
            ai_interaction_readable_logger.info("=" * 80)
            ai_interaction_readable_logger.info(formatted_prompt)
            ai_interaction_readable_logger.info("")
            ai_interaction_readable_logger.info("(Note: The above JSON schema and available actions are static and will not be repeated in subsequent logs)")
            ai_interaction_readable_logger.info("")
            self._static_prompt_logged = True
        
        def format_prompt_with_context(context: Dict[str, Any]) -> str:
            """Format the prompt with context variables."""
            # Build the full prompt with context
            prompt_parts = [formatted_prompt]
            
            # Build dynamic parts separately for logging
            dynamic_parts = []
            
            # Add context information
            if context.get("xml_context"):
                xml_string = context['xml_context']
                if not isinstance(xml_string, str):
                    xml_string = str(xml_string)
                
                xml_part = f"\n\nCurrent screen XML:\n{xml_string}"
                prompt_parts.append(xml_part)
                dynamic_parts.append(xml_part)
            
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
                    forbidden_lines = ["\n🚫 FORBIDDEN ACTIONS - DO NOT REPEAT THESE:"]
                    for action in forbidden_actions:
                        forbidden_lines.append(f"  - {action}")
                    forbidden_text = "\n".join(forbidden_lines)
                
                navigation_hints = """
Look for these navigation elements in the XML (HIGHEST PRIORITY):
- Bottom navigation tabs: tv_home, tv_assortment, tv_cart, tv_account, tv_erx, or any element with "tv_" prefix in bottom navigation area
- Navigation buttons: Any element with "nav", "menu", "tab", "bar" in resource-id
- Back buttons: Elements with "back", "arrow", "up" in resource-id or content-desc, or use the "back" action
- Menu items: Elements that clearly lead to different app sections
- Tab indicators: Elements that switch between different views/screens
"""
                
                stuck_warning = f"""
⚠️ CRITICAL: STUCK DETECTION - {stuck_reason}

You are stuck in a loop on the same screen. You MUST break out of this loop immediately.

{forbidden_text}

PRIORITY ORDER FOR YOUR NEXT ACTION (choose one):
1. 🎯 NAVIGATION ACTIONS (HIGHEST PRIORITY) - Use bottom navigation or menu items:
   - Click on navigation tabs (tv_home, tv_assortment, tv_cart, tv_account, etc.)
   - These will take you to DIFFERENT screens and break the loop
   {navigation_hints}

2. ⬅️ BACK BUTTON (HIGH PRIORITY):
   - Use the "back" action to exit this screen
   - This will return you to a previous screen

3. 📜 SCROLL ACTIONS (MEDIUM PRIORITY):
   - Only if scrolling reveals NEW navigation elements you haven't tried
   - Do NOT scroll if you've already scrolled on this screen

4. 🚫 DO NOT:
   - Repeat any of the forbidden actions listed above
   - Click buttons you've already clicked on this screen
   - Try variations of actions you've already attempted
   - Stay on this screen - you MUST navigate away

YOUR TASK: Choose an action that will take you to a DIFFERENT screen.
In your reasoning, explicitly state: "I am navigating away from this screen to break the loop by..."
"""
                prompt_parts.append(stuck_warning)
                dynamic_parts.append(stuck_warning)
            
            # Format action history
            if context.get("action_history"):
                action_history = context['action_history']
                if action_history:
                    history_lines = ["\n\nRecent Actions:"]
                    for step in action_history[-10:]:
                        step_num = step.get('step_number', '?')
                        action_desc = step.get('action_description', 'unknown action')
                        success = step.get('execution_success', False)
                        error_msg = step.get('error_message')
                        from_screen_id = step.get('from_screen_id')
                        to_screen_id = step.get('to_screen_id')
                        
                        status = "SUCCESS" if success else "FAILED"
                        details = []
                        if to_screen_id:
                            if from_screen_id == to_screen_id:
                                details.append("stayed on same screen")
                            else:
                                details.append(f"navigated to screen #{to_screen_id}")
                        elif success:
                            details.append("no navigation occurred")
                        if error_msg:
                            details.append(f"error: {error_msg}")
                        
                        detail_str = f" ({', '.join(details)})" if details else ""
                        history_lines.append(f"- Step {step_num}: {action_desc} → {status}{detail_str}")
                    
                    actions_part = "\n".join(history_lines)
                    prompt_parts.append(actions_part)
                    dynamic_parts.append(actions_part)
            
            # Format visited screens
            if context.get("visited_screens"):
                visited_screens = context['visited_screens']
                if visited_screens:
                    screens_lines = ["\n\nVisited Screens (this run):"]
                    for screen in visited_screens[:15]:
                        screen_id = screen.get('screen_id', '?')
                        activity = screen.get('activity_name', 'UnknownActivity')
                        visit_count = screen.get('visit_count', 0)
                        screens_lines.append(f"- Screen #{screen_id} ({activity}): visited {visit_count} time{'s' if visit_count != 1 else ''}")
                    
                    screens_part = "\n".join(screens_lines)
                    prompt_parts.append(screens_part)
                    dynamic_parts.append(screens_part)
            
            # Format current screen actions
            if context.get("current_screen_actions") and len(context['current_screen_actions']) > 0:
                current_screen_actions = context['current_screen_actions']
                current_screen_id = context.get('current_screen_id')
                actions_lines = [f"\n\nActions already tried on this screen (Screen #{current_screen_id}):"]
                for action in current_screen_actions:
                    action_desc = action.get('action_description', 'unknown action')
                    success = action.get('execution_success', False)
                    error_msg = action.get('error_message')
                    to_screen_id = action.get('to_screen_id')
                    
                    status = "SUCCESS" if success else "FAILED"
                    details = []
                    if to_screen_id:
                        if to_screen_id == current_screen_id:
                            details.append("stayed on same screen")
                        else:
                            details.append(f"navigated to screen #{to_screen_id}")
                    elif success:
                        details.append("no navigation occurred")
                    if error_msg:
                        details.append(f"error: {error_msg}")
                    
                    detail_str = f" ({', '.join(details)})" if details else ""
                    actions_lines.append(f"- {action_desc} → {status}{detail_str}")
                
                current_actions_part = "\n".join(actions_lines)
                prompt_parts.append(current_actions_part)
                dynamic_parts.append(current_actions_part)
            
            if context.get("last_action_feedback"):
                feedback_part = f"\n\nLast action feedback: {context['last_action_feedback']}"
                prompt_parts.append(feedback_part)
                dynamic_parts.append(feedback_part)
            
            if context.get("current_screen_visit_count"):
                visit_count_part = f"\n\nScreen visit count: {context['current_screen_visit_count']}"
                prompt_parts.append(visit_count_part)
                dynamic_parts.append(visit_count_part)
            
            closing_part = "\n\nPlease respond with a JSON object matching the schema above."
            prompt_parts.append(closing_part)
            dynamic_parts.append(closing_part)
            
            # Store dynamic parts in context for logging
            context['_dynamic_prompt_parts'] = "\n".join(dynamic_parts)
            
            # Store the full prompt in context for database storage
            full_prompt = "\n".join(prompt_parts)
            context['_full_ai_input_prompt'] = full_prompt
            
            return full_prompt
        
        def parse_json_output(llm_output: str) -> Dict[str, Any]:
            """Parse JSON from LLM output."""
            try:
                return json.loads(llm_output)
            except json.JSONDecodeError:
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', llm_output, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', llm_output, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                logger.warning(f"Could not parse JSON from LLM output: {llm_output[:200]}")
                return {}
        
        # Create chain: format prompt -> LLM -> parse JSON
        chain = RunnableLambda(format_prompt_with_context) | llm_wrapper | RunnableLambda(parse_json_output)
        return chain
