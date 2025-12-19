# ui/agent_manager.py - Handles AgentAssistant lifecycle and model switching

import logging
from typing import Optional

class AgentManager:
    """Handles AgentAssistant lifecycle and AI provider/model switching."""
    
    def __init__(self, config, log_callback):
        self.config = config
        self.log_callback = log_callback
        self.agent_assistant = None
        
    def init_agent(self, model_alias: Optional[str] = None):
        """Initialize or re-initialize the AgentAssistant."""
        try:
            from domain.agent_assistant import AgentAssistant
            
            # Cleanup old logger to avoid I/O issues
            self._cleanup_agent_logger()
            
            provider = self.config.get("AI_PROVIDER", None)
            model = model_alias or self.config.get("DEFAULT_MODEL_TYPE", None)
            
            if not provider or not model or str(model).strip() in ["", "No model selected"]:
                self.agent_assistant = None
                self.log_callback("AgentAssistant not initialized: provider or model not set.", "orange")
                return None
                
            self.agent_assistant = AgentAssistant(self.config, model_alias_override=model)
            return self.agent_assistant
        except Exception as e:
            self.agent_assistant = None
            self.log_callback(f"Failed to initialize AgentAssistant: {e}", "red")
            logging.error(f"Agent init error: {e}", exc_info=True)
            return None

    def switch_provider_model(self, provider: str, model: str):
        """Handle runtime provider/model switching."""
        try:
            self.config.update_setting_and_save("AI_PROVIDER", provider)
            self.config.update_setting_and_save("DEFAULT_MODEL_TYPE", model)
            self.init_agent(model)
            self.log_callback(f"AI switched: Provider='{provider}', Model='{model}'.", "blue")
            return True
        except Exception as e:
            self.log_callback(f"Error switching AI: {e}", "red")
            return False

    def _cleanup_agent_logger(self):
        """Clean up logging handlers for the current agent."""
        if not self.agent_assistant:
            return
            
        try:
            if hasattr(self.agent_assistant, 'ai_interaction_readable_logger'):
                logger = self.agent_assistant.ai_interaction_readable_logger
                for handler in list(logger.handlers):
                    try:
                        if isinstance(handler, logging.FileHandler):
                            handler.close()
                    except Exception:
                        pass
                    logger.removeHandler(handler)
        except Exception as e:
            logging.debug(f"Error cleaning up agent logger: {e}")
