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
                self.logit_interaction_logger.info("=" * 80)
                self.logit_interaction_logger.info(f"AI INPUT - {timestamp}")
                self.logit_interaction_logger.info("=" * 80)
                
                if "Current screen XML:" in prompt_text:
                    dynamic_start = prompt_text.find("Current screen XML:")
                    dynamic_part = prompt_text[dynamic_start:]
                    self.logit_interaction_logger.info(dynamic_part)
                else:
                    self.logit_interaction_logger.info(prompt_text)
                self.logit_interaction_logger.info("")

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
                                logger.info(f"🖼️  SENDING IMAGE TO AI: Yes (size: {prepared_image.size[0]}x{prepared_image.size[1]})")
                            else:
                                logger.warning(f"🖼️  SENDING IMAGE TO AI: No (prepared image is None)")
                        else:
                            logger.info(f"🖼️  SENDING IMAGE TO AI: No (model '{self.model_name}' does not support image context)")
                except Exception as e:
                    logger.warning(f"🖼️  SENDING IMAGE TO AI: No (error checking support: {e})", exc_info=True)

            try:
                response_text, metadata = self.model_adapter.generate_response(
                    prompt=prompt_text,
                    image=prepared_image,
                    image_format=self.cfg.get('IMAGE_FORMAT', None),
                    image_quality=self.cfg.get('IMAGE_QUALITY', None)
                )
                
                # Log the AI response
                if self.logit_interaction_logger:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.logit_interaction_logger.info("=" * 80)
                    self.logit_interaction_logger.info(f"AI RESPONSE - {timestamp}")
                    self.logit_interaction_logger.info("=" * 80)
                    self.logit_interaction_logger.info(response_text)
                    self.logit_interaction_logger.info("")
                    self.logit_interaction_logger.info("")
                
                return response_text
            except Exception as e:
                logger.error(f"Error in LangChain LLM wrapper: {e}")
                if self.logit_interaction_logger:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.logit_interaction_logger.info("=" * 80)
                    self.logit_interaction_logger.info(f"AI ERROR - {timestamp}")
                    self.logit_interaction_logger.info("=" * 80)
                    self.logit_interaction_logger.info(f"Error: {str(e)}")
                    self.logit_interaction_logger.info("")
                return ""

        return RunnableLambda(_llm_call)
