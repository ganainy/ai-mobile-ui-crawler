"""
LangChain integration wrapper for the AI agent.

Provides compatibility between the custom model adapters and LangChain's 
Runnable ecosystem, adding logging and image context support.
"""
import logging
import time
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
        self.logit_interaction_logger = interaction_logger
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

            # Log the AI input (prompt)
            if self.logit_interaction_logger:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if "Current screen XML:" in prompt_text:
                    dynamic_start = prompt_text.find("Current screen XML:")
                    dynamic_part = prompt_text[dynamic_start:]
                else:
                    pass
            
            # Log a summary of the AI input to console
            prompt_preview = prompt_text[:500] + "..." if len(prompt_text) > 500 else prompt_text

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
                                pass
                            else:
                                logger.warning(f"🖼️  SENDING IMAGE TO AI: No (prepared image is None)")
                        else:
                            pass
                except Exception as e:
                    pass
                    logger.warning(f"🖼️  SENDING IMAGE TO AI: No (error checking support: {e})", exc_info=True)

            try:
                # Start background thread to log progress while waiting for AI
                import threading
                import sys
                start_time = time.time()
                stop_logging = False
                
                def log_ai_progress():
                    while not stop_logging:
                        elapsed = time.time() - start_time
                        # Use carriage return to overwrite same line (no newline)
                        print(f"\rAI thinking... {elapsed:.1f}s   ", end='', flush=True)
                        time.sleep(5)  # Update every 5 seconds
                
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
                # Clear the progress line and print final result
                print(f"\rAI response received in {elapsed_total:.2f}s   ", flush=True)
                
                # Log the AI response
                if self.logit_interaction_logger:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                return response_text
            except Exception as e:
                logger.error(f"Error in LangChain LLM wrapper: {e}")
                if self.logit_interaction_logger:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return ""

        return RunnableLambda(_llm_call)
