import os
import uuid
import time
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from PIL import Image
from pydantic import BaseModel, ValidationError, validator

# Always use absolute import for model_adapters
from domain.model_adapters import create_model_adapter, Session
from domain.provider_utils import get_provider_api_key, get_provider_config_key, validate_provider_config
from domain.action_executor import ActionExecutor
from domain.prompt_builder import PromptBuilder
from config.numeric_constants import (
    DEFAULT_AI_PROVIDER,
    DEFAULT_MODEL_TEMP,
    DEFAULT_MAX_TOKENS,
    LONG_PRESS_MIN_DURATION_MS,
    AI_LOG_FILENAME,
)
from config.urls import ServiceURLs
from config.context_constants import ContextSource
from domain.prompts import JSON_OUTPUT_SCHEMA, get_available_actions, ACTION_DECISION_SYSTEM_PROMPT

# Update AgentAssistant to initialize AppiumDriver with a valid Config instance
from config.app_config import Config

# Import XML simplification utility
from utils.utils import simplify_xml_for_ai

# Explicitly define the Tools class
class Tools:
    def __init__(self, driver):
        self.driver = driver

# Define the Pydantic model for a single action
class ActionData(BaseModel):
    """Single action data model."""
    action: str
    action_desc: Optional[str] = None  # Brief description of what action achieves (max 50 chars)
    target_identifier: Optional[str] = None  # Optional for actions like scroll
    target_bounding_box: Optional[Dict[str, Any]] = None
    input_text: Optional[str] = None
    reasoning: str

    @validator("target_identifier", pre=True)
    def clean_target_identifier(cls, value):
        # Handle None values
        if value is None:
            return None
        # Add normalization logic for target_identifier if needed
        return str(value).strip()

    @validator("target_bounding_box", pre=True)
    def validate_bounding_box(cls, value):
        # Ensure bounding box is in the correct format
        if value is None:
            return None
        if not isinstance(value, dict) or "top_left" not in value or "bottom_right" not in value:
            raise ValueError("Invalid bounding box format")
        return value


class JournalEntry(BaseModel):
    """Single exploration journal entry."""
    action: str
    outcome: str


class ActionBatch(BaseModel):
    """Batch of actions returned by AI for multi-action execution."""
    actions: List[ActionData]
    
    @validator("actions", pre=True)
    def validate_actions(cls, v):
        """Validate and clean actions list."""
        if not isinstance(v, list):
            raise ValueError("Actions must be a list")
        if len(v) < 1:
            raise ValueError("At least one action is required")
        if len(v) > 12:
            raise ValueError("Maximum 12 actions per batch")
        return v

class AgentAssistant:
    """
    Handles interactions with AI models (Google Gemini, OpenRouter, Ollama) using adapters.
    Implements structured prompting for mobile app UI testing.
    
    The AgentAssistant can also directly perform actions using the AgentTools, allowing it to
    implement more complex behaviors like planning, self-correction, and memory.
    """
    
    def __init__(self,
                app_config: Config, 
                model_alias_override: Optional[str] = None,
                safety_settings_override: Optional[Dict] = None,
                ui_callback=None,
                tools=None):
        
        self.cfg = app_config
        
        # Fix tools initialization: Use passed app_config instead of creating new one
        if tools is None:
            from infrastructure.appium_driver import AppiumDriver
            tools = Tools(driver=AppiumDriver(self.cfg))
        
        self.tools = tools
        self.ui_callback = ui_callback
        
        # Removed unused response_cache

        # Determine which AI provider to use
        self.ai_provider = self.cfg.get('AI_PROVIDER', DEFAULT_AI_PROVIDER).lower()

        # Adapter provider override (for routing purposes without changing UI label)
        self._adapter_provider_override: Optional[str] = None

        # Get the appropriate API key based on the provider
        is_valid, error_msg = validate_provider_config(self.cfg, self.ai_provider, ServiceURLs.OLLAMA)
        if not is_valid:
            raise ValueError(error_msg or f"Unsupported AI provider: {self.ai_provider}")
        
        self.api_key = get_provider_api_key(self.cfg, self.ai_provider, ServiceURLs.OLLAMA)
        if not self.api_key:
            config_key = get_provider_config_key(self.ai_provider) or "API_KEY"
            raise ValueError(f"{config_key} is not set in the provided application configuration.")

        # Validate and set model name
        model_id = model_alias_override or self.cfg.DEFAULT_MODEL_TYPE
        self.model_name = str(model_id).strip() if model_id else ""
        
        if not self.model_name or self.model_name in ["", "No model selected", "None"]:
            raise ValueError("No model selected. Please choose a model in AI Settings (Default Model Type).")
            
        # Backward compatibility for model_alias/actual_model_name if needed by other modules
        # but we standardize on self.model_name internally
        self.model_alias = self.model_name 
        self.actual_model_name = self.model_name

        # Construct a minimal provider-agnostic model config
        model_config_from_file = {
            'name': self.model_name,
            'description': f"Direct model id '{self.model_name}' for provider '{self.ai_provider}'",
            'generation_config': {
                'temperature': DEFAULT_MODEL_TEMP,
                'top_p': 0.95,
                'max_output_tokens': DEFAULT_MAX_TOKENS
            },
            'online': self.ai_provider in [DEFAULT_AI_PROVIDER, 'openrouter']
        }

        # Initialize model
        self._initialize_model(model_config_from_file, safety_settings_override)

        # Initialize session
        self._init_session(user_id=None)
        
        # Define AI helper for text processing
        def ai_helper(prompt: str) -> str:
            """Simple helper to invoke the AI model for a single text prompt."""
            try:
                response_text, _ = self.model_adapter.generate_response(prompt)
                return response_text
            except Exception as e:
                logging.error(f"AI Helper failed: {e}")
                return ""

        # Initialize action executor
        self.action_executor = ActionExecutor(self.tools.driver, self.cfg, ai_helper=ai_helper)
        
        # Initialize prompt builder
        self.prompt_builder = PromptBuilder(self.cfg)
        
        # Initialize logger
        self._setup_ai_interaction_logger()

    def _init_session(self, user_id: Optional[str] = None):
        """Initialize a new provider-agnostic session."""
        now = time.time()
        self.session = Session(
            session_id=str(uuid.uuid4()),
            provider=self.ai_provider,
            model=self.model_name,
            created_at=now,
            last_active=now,
            metadata={
                'user_id': user_id,
                'initialized_at': now
            }
        )



    def execute_action(self, action_data: Dict[str, Any]) -> bool:
        """
        Execute an action based on the action_data dictionary.
        
        This method delegates to the ActionExecutor module which handles
        all action execution logic.
        
        Args:
            action_data: Dictionary containing action information with at least an 'action' key.
                        Expected keys: action, target_identifier, target_bounding_box, input_text, etc.
        
        Returns:
            True if action executed successfully, False otherwise
        """
        try:
            # Ensure driver is connected before executing
            if not self._ensure_driver_connected():
                logging.error("Cannot execute action: Driver not connected")
                return False
            
            # Delegate to ActionExecutor
            return self.action_executor.execute_action(action_data)
                
        except Exception as e:
            logging.error(f"Error in execute_action wrapper: {e}", exc_info=True)
            return False

    def _initialize_model(self, model_config, safety_settings_override):
        """Initialize the AI model with appropriate settings using the adapter."""
        try:
            # Check if the required dependencies are installed for the chosen provider
            from domain.model_adapters import check_dependencies
            adapter_provider = self._adapter_provider_override or self.ai_provider
            deps_installed, error_msg = check_dependencies(adapter_provider)
            
            if not deps_installed:
                logging.error(f"Missing dependencies for {adapter_provider}: {error_msg}")
                raise ImportError(error_msg)
            
            # Ensure we have a valid model name
            if not self.actual_model_name:
                raise ValueError("Model name must be provided.")
                    
            # Create model adapter
            self.model_adapter = create_model_adapter(
                provider=adapter_provider,
                api_key=self.api_key,
                model_name=self.actual_model_name
            )
            
            # Set up safety settings
            safety_settings = safety_settings_override or self.cfg.get('AI_SAFETY_SETTINGS', None)
            
            # Initialize the model adapter
            self.model_adapter.initialize(model_config, safety_settings)
            

        except Exception as e:
            logging.error(f"Failed to initialize AI model: {e}", exc_info=True)
            raise

    def _setup_ai_interaction_logger(self, force_recreate: bool = False):
        """Get reference to the shared AI interaction logger.
        
        The logger handlers are configured externally (e.g. in crawler_loop.py).
        This method just ensures we have the reference.
        """
        self.ai_interaction_readable_logger = logging.getLogger('AIInteractionReadableLogger')


    def _prepare_image_part(self, screenshot_bytes: Optional[bytes]) -> Optional[Image.Image]:
        """Prepare an image for the AI model.

        Delegates to the centralized ImagePreprocessor service.
        Screenshots are pre-processed at capture time, so this primarily
        handles RGB conversion and any provider-specific size limits.

        Args:
            screenshot_bytes: Screenshot bytes (should be already preprocessed)

        Returns:
            PIL Image ready for model encoding, or None on error
        """
        if screenshot_bytes is None:
            return None
        
        try:
            from infrastructure.image_preprocessor import get_preprocessor
            
            # Get provider-specific max width if different from global config
            ai_provider = self.cfg.get('AI_PROVIDER', DEFAULT_AI_PROVIDER).lower()
            try:
                from config.app_config import AI_PROVIDER_CAPABILITIES
            except ImportError:
                from config.app_config import AI_PROVIDER_CAPABILITIES
            
            capabilities = AI_PROVIDER_CAPABILITIES.get(ai_provider, {})
            provider_max_width = capabilities.get('image_max_width')
            
            # Use the preprocessor service
            preprocessor = get_preprocessor(self.cfg)
            return preprocessor.get_pil_image_for_ai(screenshot_bytes, max_width=provider_max_width)
            
        except Exception as e:
            logging.error(f"Failed to prepare image part for AI: {e}", exc_info=True)
            return None

    def _extract_xml_string(self, xml_context: Union[str, Dict]) -> str:
        """Extract XML string from various response formats."""
        if isinstance(xml_context, str):
            return xml_context
        
        if not isinstance(xml_context, dict):
            return str(xml_context)
        
        # Try nested path: data.data.source
        if 'data' in xml_context:
            data = xml_context['data']
            if isinstance(data, dict):
                # Check for deeply nested structure
                if 'data' in data and isinstance(data['data'], dict):
                    return data['data'].get('source') or data['data'].get('xml') or str(xml_context)
                # Check for direct structure
                return data.get('source') or data.get('xml') or str(xml_context)
        
        return str(xml_context)

    def _resolve_ocr_references(self, validated_data: Dict[str, Any], 
                               ocr_results: Optional[List[Dict]]) -> None:
        """Resolve OCR IDs to bounding boxes in-place."""
        if not ocr_results or "actions" not in validated_data:
            return
        
        for action_item in validated_data["actions"]:
            target_id = action_item.get("target_identifier")
            if not target_id or not str(target_id).startswith("ocr_"):
                continue
            
            try:
                idx = int(str(target_id).split("_")[1])
                if 0 <= idx < len(ocr_results):
                    item = ocr_results[idx]
                    bounds = item.get('bounds')
                    if bounds and len(bounds) == 4:
                        action_item["target_bounding_box"] = {
                            "top_left": [bounds[0], bounds[1]],
                            "bottom_right": [bounds[2], bounds[3]]
                        }
            except (ValueError, IndexError):
                pass
    
    def _prepare_context(self, screenshot_bytes, xml_context, ocr_results, 
                        exploration_journal, **kwargs) -> Dict[str, Any]:
        """Prepare context dictionary for AI prompt."""
        
        # Extract XML
        xml_string_raw = self._extract_xml_string(xml_context)
        
        # Simplify XML
        xml_string_simplified = xml_string_raw
        if xml_string_raw:
            try:
                from utils.utils import xml_to_structured_json
                xml_string_simplified = xml_to_structured_json(xml_string_raw)
            except Exception as e:
                logging.warning(f"XML simplification failed, using original: {e}")
                xml_string_simplified = xml_string_raw

        # Detect secure screens
        is_secure_screen = False
        if screenshot_bytes and len(screenshot_bytes) < 200:
            try:
                if b"IVBOR" in screenshot_bytes or len(screenshot_bytes) < 100:
                    is_secure_screen = True
            except Exception:
                pass
        
        if is_secure_screen:
            logging.warning("⚠️ SECURE SCREEN DETECTED: Visual context disabled.")
            screenshot_bytes = None
            warning_text = "SECURE VIEW DETECTED (FLAG_SECURE). SCREENSHOT IS BLACK. RELY ON XML HIERARCHY."
            if isinstance(xml_string_simplified, dict):
                xml_string_simplified["_WARNING"] = warning_text
            elif isinstance(xml_string_simplified, str):
                xml_string_simplified = f"<!-- ⚠️ {warning_text} -->\n" + xml_string_simplified

        # Prepare image if enabled
        self._current_prepared_image = None
        enable_image_context = self.cfg.get('ENABLE_IMAGE_CONTEXT', False)
        
        if enable_image_context and screenshot_bytes:
             try:
                 from domain.providers.registry import ProviderRegistry
                 provider_strategy = ProviderRegistry.get_by_name(self.ai_provider)
                 if provider_strategy and provider_strategy.supports_image_context(self.cfg, self.model_name):
                      self._current_prepared_image = self._prepare_image_part(screenshot_bytes)
                      if self._current_prepared_image:
                           logging.info(f"📸 Image prepared for AI: {self._current_prepared_image.size}")
             except Exception as e:
                  logging.warning(f"Error preparing image: {e}")
        elif enable_image_context and not screenshot_bytes and not is_secure_screen:
             logging.warning("📸 Image context enabled but no screenshot_bytes available")

        # Build context dict
        context = {
            "screenshot_bytes": screenshot_bytes,
            "xml_context": xml_string_simplified,
            "_full_xml_context": xml_string_raw,
            "ocr_context": ocr_results,
            "exploration_journal": exploration_journal or [],
            "app_package": self.cfg.get("APP_PACKAGE") or "",
            "current_screen_actions": kwargs.get("current_screen_actions", []),
            "current_screen_visit_count": kwargs.get("current_screen_visit_count", 0),
            "current_composite_hash": kwargs.get("current_composite_hash", ""),
            "last_action_feedback": kwargs.get("last_action_feedback", ""),
            "is_stuck": kwargs.get("is_stuck", False),
            "stuck_reason": kwargs.get("stuck_reason", ""),
            "current_screen_id": kwargs.get("current_screen_id"),
            "is_synthetic_screenshot": kwargs.get("is_synthetic_screenshot", False),
        }
        return context

    def get_next_action(self, 
                   screenshot_bytes: Optional[bytes],
                   xml_context: str,
                   ocr_results: Optional[List[Dict[str, Any]]] = None,
                   exploration_journal: Optional[List[Dict[str, str]]] = None,
                   current_screen_id: Optional[int] = None,
                   current_screen_visit_count: int = 0,
                   is_stuck: bool = False,
                   **deprecated_kwargs) -> Optional[Tuple[Dict[str, Any], float, int, Optional[str]]]:
        """Get next action from AI.
        
        Args:
            screenshot_bytes: Screenshot image bytes
            xml_context: XML representation of screen
            ocr_results: OCR detected elements
            exploration_journal: AI-maintained exploration journal
            current_screen_id: ID of current screen
            current_screen_visit_count: Number of times current screen has been visited
            is_stuck: Whether the crawler is detected to be stuck
            **deprecated_kwargs: Catches deprecated parameters (action_history, etc.)
            
        Returns:
            Tuple of (action_data dict, confidence float, token_count int, ai_input_prompt str structure) or None
        """
        if deprecated_kwargs:
            pass # Ignored parameters

        try:
            # Prepare context
            context = self._prepare_context(
                screenshot_bytes=screenshot_bytes,
                xml_context=xml_context,
                ocr_results=ocr_results,
                exploration_journal=exploration_journal,
                current_screen_id=current_screen_id,
                current_screen_visit_count=current_screen_visit_count,
                is_stuck=is_stuck,
                **deprecated_kwargs # Pass other kwargs if any are relevant
            )

            # Build Prompt
            from domain.prompts import build_action_decision_prompt
            custom_prompt_part = self.cfg.get('CRAWLER_ACTION_DECISION_PROMPT')
            prompt_template = build_action_decision_prompt(custom_prompt_part)
            full_prompt = self.prompt_builder.format_prompt(prompt_template, context)
            
            # Store for analytics
            ai_input_prompt = {
                'full_prompt': context.get('_full_ai_input_prompt', full_prompt),
                'static_part': context.get('_static_prompt_part', ''),
                'dynamic_part': context.get('_dynamic_prompt_parts', '')
            }

            # Invoke AI
            token_count = 0
            chain_result = None
            
            try:
                if self.ai_interaction_readable_logger:
                   self.ai_interaction_readable_logger.info("=== AI INPUT ===\n" + full_prompt)
                
                response_text, token_usage = self.model_adapter.generate_response(
                    prompt=full_prompt,
                    image=self._current_prepared_image
                )
                token_count = token_usage.get('total_tokens', 0) if token_usage else 0
                
                if self.ai_interaction_readable_logger:
                    self.ai_interaction_readable_logger.info("=== AI OUTPUT ===\n" + response_text)
                
                from utils.utils import parse_json_robust
                chain_result = parse_json_robust(response_text)
                
                if not chain_result:
                     logging.warning(f"Failed to parse JSON from AI response: {response_text[:200]}")
            
            except Exception as e:
                logging.error(f"Error invoking AI model: {e}")
                return None
            finally:
                self._current_prepared_image = None
            
            if not chain_result:
                return None

            # Validate and Clean
            validated_data = self._validate_and_clean_action_data(chain_result)
            
            # Resolve OCR references
            self._resolve_ocr_references(validated_data, context.get('ocr_context'))

            return validated_data, 0.0, token_count, ai_input_prompt
            
        except ValidationError as e:
            logging.error(f"Validation error in action data: {e}")
            return None
        except Exception as e:
            logging.error(f"Error in get_next_action: {e}", exc_info=True)
            return None


    def _validate_and_clean_action_data(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean action data from AI response.
        
        Handles both formats:
        1. Multi-action format: {"actions": [...]}
        2. Legacy single-action format: {"action": "...", ...}
        
        Returns:
            Validated ActionBatch as dictionary with 'actions' key (list)
        """
        # Already in batch format
        if "actions" in action_data:
            return ActionBatch.model_validate(action_data).model_dump()
        
        # Legacy single-action format - convert to batch
        if "action" in action_data:
            single_action = ActionData.model_validate(action_data)
            return ActionBatch(actions=[single_action]).model_dump()
        
        raise ValueError("Action data must contain 'actions' array or 'action' field")

    def _ensure_driver_initialized(self):
        if not self.tools:
            raise RuntimeError("Tools are not initialized.")
        if not hasattr(self.tools, 'driver') or not self.tools.driver:
            raise RuntimeError("Driver is not initialized or unavailable.")
    
    def _ensure_driver_connected(self) -> bool:
        """Ensure the driver is connected to MCP and session is initialized.
        
        Returns:
            True if driver is connected and ready, False otherwise
        """
        try:
            try:
                self._ensure_driver_initialized()
            except RuntimeError:
                return False
            
            driver = self.tools.driver
            
            # Check if session is already initialized
            if hasattr(driver, '_session_initialized') and driver._session_initialized:
                # Validate session is still active
                if driver.validate_session():
                    return True
                else:
                    logging.warning("Session validation failed, reinitializing...")
                    driver._session_initialized = False
            
            # Initialize session if not initialized
            if not driver._session_initialized:
                app_package = self.cfg.get('APP_PACKAGE')
                app_activity = self.cfg.get('APP_ACTIVITY')
                # Get device UDID from path_manager if available
                if hasattr(self.cfg, '_path_manager'):
                    device_udid = self.cfg._path_manager.get_device_udid()
                else:
                    device_udid = None
                
                if not driver.initialize_session(
                    app_package=app_package,
                    app_activity=app_activity,
                    device_udid=device_udid
                ):
                    logging.error("Failed to initialize Appium session")
                    return False
            
            return True
            
        except Exception as e:
            logging.error(f"Error ensuring driver connection: {e}", exc_info=True)
            return False

