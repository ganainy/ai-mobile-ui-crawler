import os
import io
import uuid
import time
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from PIL import Image
from pydantic import BaseModel, ValidationError, validator

# MCP client exceptions removed

# LangChain imports for orchestration
from langchain_core.runnables import RunnableLambda
from langchain_core.prompts import PromptTemplate
from langgraph.checkpoint.memory import MemorySaver

# Always use absolute import for model_adapters
from domain.model_adapters import create_model_adapter, Session
from domain.provider_utils import get_provider_api_key, get_provider_config_key, validate_provider_config
from domain.action_executor import ActionExecutor
from domain.prompt_builder import PromptBuilder, ActionDecisionChain
from domain.langchain_wrapper import LangChainWrapper
from config.numeric_constants import (
    DEFAULT_AI_PROVIDER,
    DEFAULT_MODEL_TEMP,
    DEFAULT_MAX_TOKENS,
    IMAGE_MAX_WIDTH_DEFAULT,
    IMAGE_DEFAULT_QUALITY,
    IMAGE_DEFAULT_FORMAT,
    IMAGE_DEFAULT_FORMAT,
    IMAGE_BG_COLOR,
    IMAGE_BG_COLOR,
    IMAGE_SHARPEN_RADIUS,
    IMAGE_SHARPEN_PERCENT,
    IMAGE_SHARPEN_THRESHOLD,
    LONG_PRESS_MIN_DURATION_MS,
    AI_LOG_FILENAME,
)
from config.urls import ServiceURLs
from config.context_constants import ContextSource
from domain.prompts import JSON_OUTPUT_SCHEMA, get_available_actions, ACTION_DECISION_SYSTEM_PROMPT, build_action_decision_prompt

# Update AgentAssistant to initialize AppiumDriver with a valid Config instance
from config.app_config import Config

# Import XML simplification utility
from utils.utils import simplify_xml_for_ai

# Explicitly define the Tools class
class Tools:
    def __init__(self, driver):
        self.driver = driver

# Define the Pydantic model for ActionData
class ActionData(BaseModel):
    action: str
    target_identifier: Optional[str] = None  # Optional for actions like scroll
    target_bounding_box: Optional[Dict[str, Any]] = None
    input_text: Optional[str] = None
    reasoning: str

    @validator("target_identifier")
    def clean_target_identifier(cls, value):
        # Add normalization logic for target_identifier if needed
        return value.strip()

    @validator("target_bounding_box", pre=True)
    def validate_bounding_box(cls, value):
        # Ensure bounding box is in the correct format
        if value is None:
            return None
        if not isinstance(value, dict) or "top_left" not in value or "bottom_right" not in value:
            raise ValueError("Invalid bounding box format")
        return value

class AgentAssistant:
    """
    Handles interactions with AI models (Google Gemini, OpenRouter, Ollama) using adapters.
    Implements structured prompting for mobile app UI testing.
    
    The AgentAssistant can also directly perform actions using the AgentTools, allowing it to
    implement more complex behaviors like planning, self-correction, and memory.
    """
    
    def __init__(self,
                app_config, # Type hint with your actual Config class
                model_alias_override: Optional[str] = None,
                safety_settings_override: Optional[Dict] = None,
                ui_callback=None,
                tools=None):  # Added tools parameter
        if tools is None:
            app_config = Config()
            from infrastructure.appium_driver import AppiumDriver
            tools = Tools(driver=AppiumDriver(app_config))
        
        self.tools = tools
        self.cfg = app_config
        self.response_cache: Dict[str, Tuple[Dict[str, Any], float, int]] = {}
        self.ui_callback = ui_callback  # Callback for UI updates


        # Determine which AI provider to use
        self.ai_provider = self.cfg.get('AI_PROVIDER', DEFAULT_AI_PROVIDER).lower()

        # Adapter provider override (for routing purposes without changing UI label)
        self._adapter_provider_override: Optional[str] = None

        # Get the appropriate API key based on the provider using provider-agnostic utility
        is_valid, error_msg = validate_provider_config(self.cfg, self.ai_provider, ServiceURLs.OLLAMA)
        if not is_valid:
            raise ValueError(error_msg or f"Unsupported AI provider: {self.ai_provider}")
        
        self.api_key = get_provider_api_key(self.cfg, self.ai_provider, ServiceURLs.OLLAMA)
        if not self.api_key:
            # This should not happen if validation passed, but add safety check
            config_key = get_provider_config_key(self.ai_provider) or "API_KEY"
            raise ValueError(f"{config_key} is not set in the provided application configuration.")

        # Use DEFAULT_MODEL_TYPE directly as a provider-specific model identifier
        model_id = model_alias_override or self.cfg.DEFAULT_MODEL_TYPE
        if not model_id or str(model_id).strip() in ["", "No model selected"]:
            raise ValueError("No model selected. Please choose a model in AI Settings (Default Model Type).")

        # Treat the selected value as the actual model name across providers
        self.model_alias = str(model_id)
        self.actual_model_name = str(model_id)

        # Construct a minimal provider-agnostic model config. Adapters apply defaults.
        model_config_from_file = {
            'name': self.actual_model_name,
            'description': f"Direct model id '{self.actual_model_name}' for provider '{self.ai_provider}'",
            'generation_config': {
                # Keep conservative defaults; adapters may override or apply safer fallbacks
                'temperature': DEFAULT_MODEL_TEMP,
                'top_p': 0.95,
                'max_output_tokens': DEFAULT_MAX_TOKENS
            },
            'online': self.ai_provider in [DEFAULT_AI_PROVIDER, 'openrouter']
        }

        # Initialize model using the adapter
        self._initialize_model(model_config_from_file, safety_settings_override)

        # Initialize provider-agnostic session
        self._init_session(user_id=None)
        
        # Initialize action executor (handles all action execution logic)
        self.action_executor = ActionExecutor(self.tools.driver, self.cfg)
        
        # Initialize prompt builder
        self.prompt_builder = PromptBuilder(self.cfg)
        
        # Initialize logger before LangChain components
        self._setup_ai_interaction_logger()
        
        # Initialize LangChain components for orchestration
        self._init_langchain_components()

    def _init_session(self, user_id: Optional[str] = None):
        """Initialize a new provider-agnostic session."""
        now = time.time()
        # actual_model_name is always set in __init__ before this is called
        # This fallback chain is defensive programming but should never execute
        model = self.actual_model_name if hasattr(self, 'actual_model_name') else (self.model_alias if hasattr(self, 'model_alias') else self.cfg.get('DEFAULT_MODEL_TYPE', None))
        if not model:
            # This should never happen due to validation in __init__, but fail fast if it does
            raise ValueError("No model available for session initialization")
        self.session = Session(
            session_id=str(uuid.uuid4()),
            provider=self.ai_provider,
            model=str(model),
            created_at=now,
            last_active=now,
            metadata={
                'user_id': user_id,
                'initialized_at': now
            }
        )

    def _init_langchain_components(self):
        """Initialize LangChain components for orchestration."""
        try:

            # Create the LLM wrapper
            wrapper = LangChainWrapper(
                model_adapter=self.model_adapter,
                config=self.cfg,
                ai_provider=self.ai_provider,
                model_name=self.actual_model_name,
                interaction_logger=self.ai_interaction_readable_logger,
                get_current_image=lambda: getattr(self, '_current_prepared_image', None)
            )
            self.langchain_llm = wrapper.create_llm_wrapper()

            # Create the action decision chain
            custom_prompt_part = self.cfg.CRAWLER_ACTION_DECISION_PROMPT
            action_decision_prompt = build_action_decision_prompt(custom_prompt_part)
            
            action_chain = self.prompt_builder.create_prompt_chain(
                action_decision_prompt, 
                self.langchain_llm,
                self.ai_interaction_readable_logger
            )
            self.action_decision_chain = ActionDecisionChain(chain=action_chain)

            # Initialize memory checkpointer for cross-request context
            self.langchain_memory = MemorySaver()


        except Exception as e:
            logging.error(f"Failed to initialize LangChain components: {e}", exc_info=True)
            raise

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
        """Initializes only the human-readable logger (JSONL removed).
        
        Args:
            force_recreate: If True, close existing handlers and recreate them.
        """
        # Get the logger instance (shared across all AgentAssistant instances)
        logger = logging.getLogger('AIInteractionReadableLogger')
        
        # Set self.ai_interaction_readable_logger to the logger instance
        self.ai_interaction_readable_logger = logger
        
        # Clean up any closed or invalid handlers before checking
        if logger.handlers:
            for handler in list(logger.handlers):
                try:
                    # Check if handler is closed or invalid
                    if isinstance(handler, logging.FileHandler):
                        # Try to access the stream to see if it's closed
                        if hasattr(handler, 'stream') and handler.stream:
                            try:
                                # Check if stream is closed
                                if handler.stream.closed:
                                    logger.removeHandler(handler)
                                    continue
                            except (AttributeError, ValueError):
                                # Stream might be invalid, remove handler
                                logger.removeHandler(handler)
                                continue
                except Exception:
                    # If we can't check the handler, remove it to be safe
                    try:
                        logger.removeHandler(handler)
                    except Exception:
                        pass
        
        if logger.handlers and not force_recreate:
            return  # Already configured

        # Close existing file handlers if recreating
        if force_recreate and logger.handlers:
            for handler in list(logger.handlers):
                if isinstance(handler, logging.FileHandler):
                    try:
                        handler.close()
                    except Exception:
                        pass
                logger.removeHandler(handler)

        # Use the LOG_DIR property which resolves the template properly
        try:
            target_log_dir = self.cfg.LOG_DIR if hasattr(self.cfg, 'LOG_DIR') else self.cfg.get('LOG_DIR', None)
        except Exception as e:
            # Only log warning if it's NOT the expected "APP_PACKAGE not set" error
            if "APP_PACKAGE must be set" not in str(e):
                logging.warning(f"Could not get LOG_DIR property: {e}, trying get() method")
            target_log_dir = self.cfg.get('LOG_DIR', None)
        
        # Don't create directory here - it will be created when the file handler is created
        # This allows path regeneration to work without directory locks
        
        # Configure logger settings
        # Configure logger settings
        logger.setLevel(logging.INFO)
        logger.propagate = True  # Propagate to root logger (which writes to crawler.log)
        
        # We don't add specific handlers anymore - we rely on the root logger's handler
        # which is configured in crawler_loop.py to write to the single log file.
        
        # Helper logic to ensure no old handlers remain
        for handler in list(logger.handlers):
            try:
                logger.removeHandler(handler)
            except Exception:
                pass


    def _prepare_image_part(self, screenshot_bytes: Optional[bytes]) -> Optional[Image.Image]:
        """Prepare an image for the agent with config-driven preprocessing before model encoding.

        Steps:
        - Decode screenshot bytes to PIL Image
        - Optional: Crop status/nav bars using configured percentages
        - Resize down to configured max width (no upscaling), preserve aspect ratio
        - Convert to RGB for consistent compression downstream
        - Apply mild sharpening to preserve text clarity
        - Return processed PIL Image (model adapters will handle provider-specific encoding)
        """
        if screenshot_bytes is None:
            return None
            
        try:
            img = Image.open(io.BytesIO(screenshot_bytes))
            original_size = len(screenshot_bytes)
            
            # Get AI provider for provider-specific optimizations
            ai_provider = self.cfg.get('AI_PROVIDER', DEFAULT_AI_PROVIDER).lower()
            
            # Get provider capabilities from config
            try:
                from config.app_config import AI_PROVIDER_CAPABILITIES
            except ImportError:
                from config.app_config import AI_PROVIDER_CAPABILITIES
            
            capabilities = AI_PROVIDER_CAPABILITIES.get(ai_provider, AI_PROVIDER_CAPABILITIES.get(DEFAULT_AI_PROVIDER, {}))
            
            # Resolve preprocessing settings (global overrides take precedence)
            max_width = self.cfg.get('IMAGE_MAX_WIDTH', None) or capabilities.get('image_max_width', IMAGE_MAX_WIDTH_DEFAULT)
            quality = self.cfg.get('IMAGE_QUALITY', None) or capabilities.get('image_quality', IMAGE_DEFAULT_QUALITY)
            image_format = self.cfg.get('IMAGE_FORMAT', None) or capabilities.get('image_format', IMAGE_DEFAULT_FORMAT)
            image_format = self.cfg.get('IMAGE_FORMAT', None) or capabilities.get('image_format', IMAGE_DEFAULT_FORMAT)
            
            # Resize if necessary (maintain aspect ratio)
            if img.width > max_width:
                scale = max_width / img.width
                new_height = int(img.height * scale)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary (for JPEG compatibility and better compression)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparent images
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, IMAGE_BG_COLOR)

                    background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
                    img = background
                else:
                    img = img.convert('RGB')
            
            # Apply sharpening to maintain text clarity after compression
            from PIL import ImageFilter

            # Mild sharpening to preserve text readability
            img = img.filter(ImageFilter.UnsharpMask(radius=IMAGE_SHARPEN_RADIUS, percent=IMAGE_SHARPEN_PERCENT, threshold=IMAGE_SHARPEN_THRESHOLD))
            
            # Note: We return the processed PIL Image. Encoding (format/quality) is handled by model adapters.
            # Still, estimate potential savings for logging by encoding briefly to measure size.
            try:
                compressed_buffer = io.BytesIO()
                if image_format.upper() == IMAGE_DEFAULT_FORMAT:
                    img.save(
                        compressed_buffer,
                        format=IMAGE_DEFAULT_FORMAT,
                        quality=quality,
                        optimize=True,
                        progressive=True,
                        subsampling='4:2:0'
                    )
                else:
                    img.save(compressed_buffer, format=image_format, optimize=True)
                compressed_size = compressed_buffer.tell()
                compression_ratio = original_size / compressed_size if compressed_size > 0 else 1
            except Exception as est_err:
                pass
            
            return img
            
        except Exception as e:
            logging.error(f"Failed to prepare image part for AI: {e}", exc_info=True)
            return None

    def _get_next_action_langchain(self, screenshot_bytes: Optional[bytes], xml_context: str, 
                                   action_history: Optional[List[Dict[str, Any]]] = None,
                                   visited_screens: Optional[List[Dict[str, Any]]] = None,
                                   current_screen_actions: Optional[List[Dict[str, Any]]] = None,
                                   current_screen_id: Optional[int] = None,
                                   current_screen_visit_count: int = 0, 
                                   current_composite_hash: str = "", 
                                   last_action_feedback: Optional[str] = None,
                                   is_stuck: bool = False,
                                   stuck_reason: Optional[str] = None,
                                   ocr_results: Optional[List[Dict[str, Any]]] = None,
                                   exploration_journal: Optional[str] = None) -> Optional[Tuple[Dict[str, Any], float, int, Optional[str], Optional[str]]]:
        """Get the next action using LangChain decision chain.
        
        Args:
            screenshot_bytes: Screenshot image bytes (optional, for future vision support)
            xml_context: XML representation of current screen
            action_history: List of structured action history entries with success/failure info (DEPRECATED - use exploration_journal)
            visited_screens: List of visited screens with visit counts (DEPRECATED - use exploration_journal)
            current_screen_actions: List of actions already tried on current screen (DEPRECATED - use exploration_journal)
            current_screen_id: ID of current screen (if known)
            current_screen_visit_count: Number of times current screen has been visited
            current_composite_hash: Hash of current screen state
            last_action_feedback: Feedback from last action execution
            is_stuck: Whether the crawler is detected to be stuck on the same screen
            stuck_reason: Reason why the crawler is considered stuck
            ocr_results: List of OCR detected elements (text, bounds, confidence)
            exploration_journal: AI-maintained exploration journal (replaces action_history, visited_screens, current_screen_actions)
            
        Returns:
            Tuple of (action_data dict, confidence float, token_count int, ai_input_prompt str, exploration_journal str) or None on error
        """
        try:
            # Get context sources - HYBRID (XML+OCR) is always enabled
            context_source = self.cfg.CONTEXT_SOURCE or [ContextSource.HYBRID]
            
            # HYBRID is always on, so XML and OCR are always included
            # IMAGE is optional based on whether it's in context_source
            
            # Prepare context for the chain - always include OCR
            context = {
                "screenshot_bytes": screenshot_bytes,
                "xml_context": None,  # Will be set below
                "ocr_context": ocr_results,  # Always included with HYBRID
                "exploration_journal": exploration_journal or "",
                "current_screen_actions": current_screen_actions or [],  # For stuck detection
                "current_screen_id": current_screen_id,
                "current_screen_visit_count": current_screen_visit_count or 0,
                "current_composite_hash": current_composite_hash or "",
                "last_action_feedback": last_action_feedback or "",
                "is_stuck": is_stuck,
                "stuck_reason": stuck_reason or ""
            }

            # Extract actual XML string and simplify it before sending to AI
            xml_string_raw = xml_context
            if isinstance(xml_context, dict):
                # Handle nested MCP response structure: data.data.source or data.source
                if 'data' in xml_context:
                    data = xml_context['data']
                    if isinstance(data, dict):
                        # Check for nested data structure (data.data.source)
                        if 'data' in data and isinstance(data['data'], dict):
                            xml_string_raw = data['data'].get('source') or data['data'].get('xml') or str(xml_context)
                        else:
                            # Direct data.source
                            xml_string_raw = data.get('source') or data.get('xml') or str(xml_context)
                    else:
                        xml_string_raw = str(xml_context)
                else:
                    xml_string_raw = str(xml_context)
            elif not isinstance(xml_string_raw, str):
                xml_string_raw = str(xml_string_raw)
            
            # Clean and simplify XML before sending to AI - ALWAYS do this since HYBRID is always on
            xml_string_simplified = xml_string_raw
            if xml_string_raw:
                try:
                    # UPDATED: Use structured JSON instead of XML string
                    from utils.utils import xml_to_structured_json
                    xml_string_simplified = xml_to_structured_json(xml_string_raw)
                except Exception as e:
                    logging.warning(f"XML simplification failed, using original: {e}")
                    xml_string_simplified = xml_string_raw
            
            # Always set XML context since HYBRID is always on
            context['xml_context'] = xml_string_simplified
            context['_full_xml_context'] = xml_string_raw  # Store original for reference
            
            # Prepare image if ENABLE_IMAGE_CONTEXT is enabled
            # Store it in self so the LLM wrapper can access it
            self._current_prepared_image = None
            enable_image_context = self.cfg.get('ENABLE_IMAGE_CONTEXT', False)
            
            # Log image context status
            if enable_image_context:
                logging.info(f"📸 Image context is ENABLED (screenshot_bytes: {len(screenshot_bytes) if screenshot_bytes else 0} bytes)")
            else:
                logging.debug("Image context is disabled")
            
            if enable_image_context and screenshot_bytes:
                try:
                    # Check if provider/model supports image context before preparing
                    from domain.providers.registry import ProviderRegistry
                    provider_strategy = ProviderRegistry.get_by_name(self.ai_provider)
                    if provider_strategy:
                        model_name = self.actual_model_name if hasattr(self, 'actual_model_name') else self.model_alias
                        if provider_strategy.supports_image_context(self.cfg, model_name):
                            # Prepare the image using existing method
                            prepared_image = self._prepare_image_part(screenshot_bytes)
                            if prepared_image:
                                self._current_prepared_image = prepared_image
                                logging.info(f"📸 Image prepared for AI: {prepared_image.size[0]}x{prepared_image.size[1]}")
                        else:
                            logging.warning(f"📸 Model '{model_name}' does not support image context")
                    else:
                        logging.warning(f"📸 Provider '{self.ai_provider}' not found in registry")
                except Exception as e:
                    logging.warning(f"📸 Error preparing image for AI: {e}")
            elif enable_image_context and not screenshot_bytes:
                logging.warning("📸 Image context enabled but no screenshot_bytes available")

            
            # Log the decision request context
            if self.ai_interaction_readable_logger:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if is_stuck:
                    pass
                
                # Log the simplified XML context that will be sent to AI

            # Run the decision chain
            try:
                chain_result = self.action_decision_chain.run(context=context)
            finally:
                # Clear the prepared image after use to avoid memory leaks
                self._current_prepared_image = None
            
            # Extract the AI input prompt from context (stored by format_prompt_with_context)
            ai_input_prompt = {
                'full_prompt': context.get('_full_ai_input_prompt', ''),
                'static_part': context.get('_static_prompt_part', ''),
                'dynamic_part': context.get('_dynamic_prompt_parts', '')
            }
            
            # Log the parsed result
            if self.ai_interaction_readable_logger:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Validate and clean the result
            if not chain_result:
                logging.warning("Chain returned empty result")
                return None
            
            validated_data = self._validate_and_clean_action_data(chain_result)
            
            # Post-processing: Resolve OCR IDs to coordinates if needed
            if validated_data:
                target_id = validated_data.get("target_identifier")
                
                # With HYBRID always enabled, OCR is always on - resolve ocr_X targets to bounding boxes
                if target_id and str(target_id).startswith("ocr_") and ocr_results:
                    try:
                        # Extract index from "ocr_X"
                        idx = int(str(target_id).split("_")[1])
                        if 0 <= idx < len(ocr_results):
                            item = ocr_results[idx]
                            bounds = item.get('bounds') # [x_min, y_min, x_max, y_max]
                            
                            if bounds and len(bounds) == 4:
                                # Convert to bbox expected by tap method
                                bbox = {
                                    "top_left": [bounds[0], bounds[1]],
                                    "bottom_right": [bounds[2], bounds[3]]
                                }
                                validated_data["target_bounding_box"] = bbox
                    except (ValueError, IndexError) as e:
                        logging.warning(f"Failed to resolve OCR target {target_id}: {e}")

            # Return with metadata (confidence and token count are placeholders for now)
            # Include the AI input prompt for database storage
            # Also include the exploration_journal from the AI response
            new_exploration_journal = chain_result.get('exploration_journal', '') if chain_result else ''
            return validated_data, 0.0, 0, ai_input_prompt, new_exploration_journal
            
        except ValidationError as e:
            # Clear prepared image on error
            self._current_prepared_image = None
            logging.error(f"Validation error in action data: {e}")
            if self.ai_interaction_readable_logger:
                pass
            return None
        except Exception as e:
            # Clear prepared image on error
            self._current_prepared_image = None
            logging.error(f"Error getting next action from LangChain: {e}", exc_info=True)
            if self.ai_interaction_readable_logger:
                pass
            return None


    def _validate_and_clean_action_data(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        return ActionData.model_validate(action_data).dict()

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

    def _initialize_action_decision_chain(self):
        if not self.action_decision_chain:
            # Properly initialize action_decision_chain here
            self.action_decision_chain = ActionDecisionChain(chain=self._create_prompt_chain(ACTION_DECISION_SYSTEM_PROMPT))  # Replace with actual initialization logic