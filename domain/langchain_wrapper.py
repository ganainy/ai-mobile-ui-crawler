"""
LangChain integration wrapper for the AI agent.

Provides compatibility between the custom model adapters and LangChain's 
Runnable ecosystem, adding logging and image context support.
"""
import logging
import time
import json
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Union

from langchain_core.runnables import RunnableLambda

logger = logging.getLogger(__name__)


class LangChainWrapper:
    """
    Wraps model adapters to be compatible with LangChain.
    
    Handles the details of logging AI interactions to a readable format
    and preparing image context for multi-modal models.
    """
    
    def __init__(self, 
                 model_adapter, 
                 config, 
                 ai_provider: str, 
                 model_name: str, 
                 interaction_logger=None,
                 get_current_image: Optional[Callable[[], Optional[Any]]] = None):
        """
        Initialize the LangChainWrapper.
        
        Args:
            model_adapter: Model adapter instance (Gemini, OpenRouter, etc.)
            config: Application configuration
            ai_provider: Name of the AI provider
            model_name: Name/ID of the model
            interaction_logger: Optional logger for AI inputs/outputs
            get_current_image: Optional callable to get the latest prepared image
        """
        self.model_adapter = model_adapter
        self.cfg = config
        self.ai_provider = ai_provider
        self.model_name = model_name
        self.interaction_logger = interaction_logger
        self.get_current_image = get_current_image

    def create_llm_wrapper(self):
        """Create a LangChain-compatible LLM wrapper."""
        
        def _llm_call(prompt_input) -> str:
            """Call the model adapter and return response text."""
            # Handle different input types from LangChain
            if hasattr(prompt_input, 'messages'):
                # ChatPromptValue - extract text from messages
                prompt_text = ""
                for message in prompt_input.messages:
                    if hasattr(message, 'content'):
                        prompt_text += str(message.content) + "\n"
            elif hasattr(prompt_input, 'content'):
                # Single message
                prompt_text = str(prompt_input.content)
            else:
                # Plain string
                prompt_text = str(prompt_input)

            # Emit Prompt for UI (always, even if logger not configured)
            try:
                payload = {
                    "type": "ui_event",
                    "kind": "ai_prompt",
                    "data": prompt_text,
                    "timestamp": datetime.now().isoformat()
                }
                print(f"JSON_IPC:{json.dumps(payload)}", flush=True)
            except Exception:
                pass

            # Determine if we should include image context
            prepared_image = None
            enable_image_context = self.cfg.get('ENABLE_IMAGE_CONTEXT', False)
            
            if enable_image_context and self.get_current_image:
                try:
                    from domain.providers.registry import ProviderRegistry
                    provider_strategy = ProviderRegistry.get_by_name(self.ai_provider)
                    if provider_strategy:
                        if provider_strategy.supports_image_context(self.cfg, self.model_name):
                            prepared_image = self.get_current_image()
                            if prepared_image:
                                logger.info(f"📸 Image context: Including prepared image in AI request (size: {prepared_image.size})")
                            else:
                                logger.warning("Image context enabled but prepared image is None")
                except Exception as e:
                    logger.warning(f"Error checking image support: {e}")

            try:
                # Start background thread to log progress while waiting for AI
                import threading
                start_time = time.time()
                stop_logging = False
                
                def log_ai_progress():
                    while not stop_logging:
                        elapsed = time.time() - start_time
                        payload = {
                            "type": "ui_event", 
                            "kind": "log", 
                            "data": {'level': 'INFO', 'message': f"AI thinking... {elapsed:.1f}s"},
                            "timestamp": datetime.now().isoformat()
                        }
                        print(f"JSON_IPC:{json.dumps(payload)}", flush=True)
                        time.sleep(5)
                
                log_thread = threading.Thread(target=log_ai_progress)
                log_thread.daemon = True
                log_thread.start()
                
                try:
                    response_text, metadata = self.model_adapter.generate_response(
                        prompt=prompt_text,
                        image=prepared_image,
                        image_format=self.cfg.get('IMAGE_FORMAT', None),
                        image_quality=self.cfg.get('IMAGE_QUALITY', None)
                    )
                finally:
                    stop_logging = True
                    log_thread.join(timeout=1.0)
                
                elapsed_total = time.time() - start_time
                image_info = f" (with image)" if prepared_image else " (text only)"
                msg = f"AI response received in {elapsed_total:.2f}s{image_info}"
                payload = {
                    "type": "ui_event", 
                    "kind": "log", 
                    "data": {'level': 'INFO', 'message': msg},
                    "timestamp": datetime.now().isoformat()
                }
                print(f"JSON_IPC:{json.dumps(payload)}", flush=True)
                
                # Emit Response for UI
                try:
                    resp_data = response_text
                    try:
                        resp_data = json.loads(response_text)
                    except:
                        pass
                        
                    payload = {
                        "type": "ui_event",
                        "kind": "ai_response", 
                        "data": resp_data,
                        "timestamp": datetime.now().isoformat()
                    }
                    print(f"JSON_IPC:{json.dumps(payload)}", flush=True)
                except Exception:
                    pass
                
                return response_text
            except Exception as e:
                logger.error(f"Error in LangChain LLM wrapper: {e}")
                if self.interaction_logger:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.interaction_logger.error(f"[{timestamp}] AI ERROR: {e}")
                return ""

        return RunnableLambda(_llm_call)

