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
        
        # Get test credentials from config (with defaults)
        test_email = self.cfg.get('TEST_EMAIL') or 'test@email.com'
        test_password = self.cfg.get('TEST_PASSWORD') or 'Test123!'
        
        # Create formatted prompt string
        formatted_prompt = prompt_template.format(
            json_schema=json_output_guidance,
            action_list=action_list_str,
            journal_max_length=journal_max_length,
            test_email=test_email,
            test_password=test_password
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
        # --- STATIC PART GENERATION (Instructions, Rules, Definitions) ---
        # User requested to ALWAYS include static part since model has no memory
        
        formatted_prompt = static_prompt_part
        if formatted_prompt is None:
            # Fallback if not injected by chain
            available_actions = get_available_actions(self.cfg)
             # Override available actions if provided in context (for preview)
            if context.get('available_actions'):
                 available_actions = context['available_actions']
                 
            action_list_str = "\n".join([f"- {action}: {desc}" for action, desc in available_actions.items()])
            json_output_guidance = json.dumps(JSON_OUTPUT_SCHEMA, indent=2)
            
            # Get journal max length from config or use default
            journal_max_length = self.cfg.get('EXPLORATION_JOURNAL_MAX_LENGTH', EXPLORATION_JOURNAL_MAX_LENGTH_DEFAULT)
            
            # Get test credentials from config (with defaults)
            test_email = self.cfg.get('TEST_EMAIL') or 'test@email.com'
            test_password = self.cfg.get('TEST_PASSWORD') or 'Test123!'
            
            formatted_prompt = prompt_template.format(
                json_schema=json_output_guidance,
                action_list=action_list_str,
                journal_max_length=journal_max_length,
                test_email=test_email,
                test_password=test_password
            )

        prompt_parts = []
        
        # Always include static context
        prompt_parts.append("=== CONTEXT (Static - Instructions) ===")
        prompt_parts.append(formatted_prompt)
        
        # --- DYNAMIC PART GENERATION ---
        dynamic_parts = []
        dynamic_parts.append("\n=== CURRENT STATE ===")
        
        # Screen Visit Count
        if context.get("current_screen_visit_count"):
             dynamic_parts.append(f"**Screen Visit Context**: Visited {context['current_screen_visit_count']} times.")
        
        # Last Action Feedback (Critical)
        if context.get("last_action_feedback"):
            feedback = context['last_action_feedback']
            dynamic_parts.append(f"**Last Action Outcome**:\n{feedback}")

        # XML Context (Structured)
        if context.get("xml_context"):
            xml_data = context['xml_context']
            # It should be a JSON string from xml_to_structured_json
            # We can present it as a code block
            dynamic_parts.append(f"\n**UI Elements (JSON Structure)**:\n```json\n{xml_data}\n```")

        # OCR Context (Compact)
        if context.get("ocr_context"):
            ocr_items = context['ocr_context']
            if ocr_items:
                ocr_lines = ["\n**Visual Elements (OCR)**:"]
                # Filter/Compact logic
                for idx, item in enumerate(ocr_items):
                    text = item.get('text', '').strip()
                    elem_id = f"ocr_{idx}"
                    bounds = item.get('bounds')
                    # Compact line
                    ocr_lines.append(f"• {elem_id} = \"{text}\" {bounds}")
                
                dynamic_parts.append("\n".join(ocr_lines))
        
        # Stuck Detection
        if context.get("is_stuck"):
            stuck_reason = context.get("stuck_reason", "Multiple actions on same screen")
            stuck_part = f"\n⚠️ **STUCK DETECTED**: {stuck_reason}. YOU MUST ESCAPE. Do not repeat previous actions."
            dynamic_parts.append(stuck_part)

        # Journal
        exploration_journal = context.get("exploration_journal", "")
        if exploration_journal:
             dynamic_parts.append(f"\n=== EXPLORATION JOURNAL ===\n{exploration_journal}")
        else:
             dynamic_parts.append(f"\n=== EXPLORATION JOURNAL ===\n(Empty - Start of session)")

        # Actions Already Tried (Lightweight)
        current_screen_actions = context.get("current_screen_actions", [])
        if current_screen_actions:
            current_screen_id = context.get('current_screen_id')
            actions_lines = [f"\n**Actions Tried on This Screen (#{current_screen_id})**:"]
            for action in current_screen_actions[-8:]:
                 action_desc = action.get('action_description', 'unknown')
                 success = action.get('execution_success', False)
                 to_screen_id = action.get('to_screen_id')
                 result = f"-> Screen #{to_screen_id}" if (success and to_screen_id != current_screen_id) else "-> Ineffective/Failed"
                 actions_lines.append(f"- {action_desc} {result}")
            dynamic_parts.append("\n".join(actions_lines))

        # Test Credentials - Check credential store for this app
        app_package = context.get('app_package')
        stored_creds = None
        has_stored_creds = False
        
        if app_package:
            try:
                from infrastructure.credential_store import get_credential_store
                cred_store = get_credential_store()
                stored_creds = cred_store.get_credentials(app_package)
                has_stored_creds = stored_creds is not None
            except Exception as e:
                logger.debug(f"Could not check credential store: {e}")
        
        if has_stored_creds and stored_creds:
            # We have stored credentials for this app - use LOGIN
            email = stored_creds.get('email', '')
            password = stored_creds.get('password', '')
            name = stored_creds.get('name', '')
            dynamic_parts.append(f"""
**AUTHENTICATION STRATEGY**: 🔑 LOGIN (credentials exist for this app)
- Email: {email}
- Password: {password}
- Name: {name if name else 'N/A'}
→ When you see a login/signup choice, CHOOSE LOGIN and use these credentials.""")
        else:
            # No stored credentials - use SIGNUP then we'll store them
            test_email = self.cfg.get("TEST_EMAIL") or "test@email.com"
            test_password = self.cfg.get("TEST_PASSWORD") or "Test123!"
            test_name = self.cfg.get("TEST_NAME") or "Test User"
            dynamic_parts.append(f"""
**AUTHENTICATION STRATEGY**: 📝 SIGNUP (no stored credentials for this app)
- Email: {test_email}
- Password: {test_password}
- Name: {test_name}
→ When you see a login/signup choice, CHOOSE SIGNUP and create a new account.
→ IMPORTANT: After completing signup successfully, set "signup_completed": true in your response to save credentials for future logins.""")

        # Closing
        dynamic_parts.append("\n\n**TASK**: Choose the next best action to maximize coverage. Respond in JSON.")
        
        prompt_parts.extend(dynamic_parts)
        
        # Combine
        full_prompt = "\n".join(prompt_parts)
        
        # Store for logging
        context['_dynamic_prompt_parts'] = "\n".join(dynamic_parts)
        context['_static_prompt_part'] = formatted_prompt # Keep referencing full static for debug even if not sent
        context['_full_ai_input_prompt'] = full_prompt
        
        return full_prompt
