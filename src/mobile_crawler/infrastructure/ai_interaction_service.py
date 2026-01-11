"""AI interaction service for coordinating AI model calls."""

import json
import time
from datetime import datetime
from typing import Optional, Protocol

from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.domain.model_adapters import ModelAdapter
from mobile_crawler.domain.models import AIAction, AIResponse, BoundingBox
from mobile_crawler.domain.prompt_builder import PromptBuilder
from mobile_crawler.infrastructure.ai_interaction_repository import AIInteraction, AIInteractionRepository


class AIEventListener(Protocol):
    """Protocol for AI event listeners."""
    
    def on_ai_request_sent(self, run_id: int, step_number: int, request_data: dict) -> None:
        """Called when AI request is sent."""
        ...
    
    def on_ai_response_received(self, run_id: int, step_number: int, response_data: dict) -> None:
        """Called when AI response is received."""
        ...


class AIInteractionService:
    """Service for handling AI model interactions with retry logic and logging."""

    def __init__(
        self,
        model_adapter: ModelAdapter,
        prompt_builder: PromptBuilder,
        ai_interaction_repository: AIInteractionRepository,
        config_manager: ConfigManager,
        event_listener: Optional[AIEventListener] = None
    ):
        """Initialize AI interaction service.

        Args:
            model_adapter: The AI model adapter to use
            prompt_builder: Builder for creating prompts
            ai_interaction_repository: Repository for logging interactions
            config_manager: Configuration manager
            event_listener: Optional event listener for AI events
        """
        self.model_adapter = model_adapter
        self.prompt_builder = prompt_builder
        self.ai_interaction_repository = ai_interaction_repository
        self.config_manager = config_manager
        self.event_listener = event_listener

    @classmethod
    def from_config(cls, config_manager: ConfigManager, event_listener: Optional[AIEventListener] = None) -> 'AIInteractionService':
        """Create AI interaction service from configuration.
        
        Args:
            config_manager: Configuration manager
            event_listener: Optional event listener for AI events
            
        Returns:
            Configured AI interaction service
        """
        # Import here to avoid circular imports
        from mobile_crawler.domain.prompt_builder import PromptBuilder
        from mobile_crawler.infrastructure.ai_interaction_repository import AIInteractionRepository
        from mobile_crawler.infrastructure.database import DatabaseManager
        from mobile_crawler.infrastructure.step_log_repository import StepLogRepository
        
        # Create model adapter based on provider
        provider = config_manager.get('ai_provider', 'gemini')
        model_name = config_manager.get('ai_model', 'gemini-1.5-flash')
        
        model_adapter = cls._create_model_adapter(provider, model_name, config_manager)
        
        # Create other dependencies
        db = DatabaseManager()
        step_log_repo = StepLogRepository(db)
        prompt_builder = PromptBuilder(config_manager, step_log_repo)
        ai_repo = AIInteractionRepository(db)
        
        return cls(model_adapter, prompt_builder, ai_repo, config_manager, event_listener)
    
    @staticmethod
    def _create_model_adapter(provider: str, model_name: str, config_manager: ConfigManager) -> ModelAdapter:
        """Create model adapter based on provider.
        
        Args:
            provider: AI provider name
            model_name: Model name
            config_manager: Configuration manager
            
        Returns:
            Configured model adapter
        """
        if provider == 'mock':
            # Import here to avoid import errors in production
            from mobile_crawler.domain.providers.mock_adapter import MockAdapter
            return MockAdapter()
        elif provider == 'gemini':
            from mobile_crawler.domain.providers.gemini_adapter import GeminiAdapter
            api_key = config_manager.get('gemini_api_key')
            if not api_key:
                raise ValueError("Gemini API key not configured")
            adapter = GeminiAdapter()
            adapter.initialize({'model': model_name, 'api_key': api_key}, {})
            return adapter
        elif provider == 'openrouter':
            from mobile_crawler.domain.providers.openrouter_adapter import OpenRouterAdapter
            api_key = config_manager.get('openrouter_api_key')
            if not api_key:
                raise ValueError("OpenRouter API key not configured")
            adapter = OpenRouterAdapter()
            adapter.initialize({'model': model_name, 'api_key': api_key}, {})
            return adapter
        elif provider == 'ollama':
            from mobile_crawler.domain.providers.ollama_adapter import OllamaAdapter
            adapter = OllamaAdapter()
            adapter.initialize({'model': model_name}, {})
            return adapter
        else:
            raise ValueError(f"Unknown AI provider: {provider}")

    def get_next_actions(
        self,
        run_id: int,
        step_number: int,
        screenshot_b64: str,
        screenshot_path: Optional[str],
        is_stuck: bool = False,
        stuck_reason: Optional[str] = None,
        current_screen_id: Optional[int] = None,
        current_screen_is_new: Optional[bool] = None,
        total_unique_screens: Optional[int] = None
    ) -> AIResponse:
        """Get next actions from AI model.

        Args:
            run_id: Current run ID
            step_number: Current step number
            screenshot_b64: Base64 encoded screenshot
            screenshot_path: Path to screenshot file
            is_stuck: Whether the crawler is currently stuck
            stuck_reason: Reason for being stuck
            current_screen_id: ID of the current screen (for novelty context)
            current_screen_is_new: Whether the current screen is newly discovered
            total_unique_screens: Total unique screens discovered so far

        Returns:
            AIResponse with actions and signup completion status

        Raises:
            Exception: If all retry attempts fail
        """
        max_retries = self.config_manager.get('ai_retry_count', 2)
        
        # Build the user prompt with screen context
        user_prompt = self.prompt_builder.build_user_prompt(
            screenshot_b64=screenshot_b64,
            run_id=run_id,
            is_stuck=is_stuck,
            stuck_reason=stuck_reason,
            current_screen_id=current_screen_id,
            current_screen_is_new=current_screen_is_new,
            total_unique_screens=total_unique_screens
        )
        
        # Get system prompt
        system_prompt = self.prompt_builder.build_system_prompt()
        
        request_data = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt
        }
        request_json = json.dumps(request_data)
        
        # Emit request sent event
        if self.event_listener:
            self.event_listener.on_ai_request_sent(run_id, step_number, request_data)
        
        last_exception = None
        
        for retry_count in range(max_retries + 1):
            try:
                # Call the AI model
                start_time = time.time()
                response_text, usage_info = self.model_adapter.generate_response(
                    system_prompt, user_prompt
                )
                latency_ms = (time.time() - start_time) * 1000
                
                # Parse and validate response
                ai_response = self._parse_ai_response(response_text)
                
                # Set latency on the response
                ai_response.latency_ms = latency_ms
                
                # Log successful interaction
                interaction = AIInteraction(
                    id=None,
                    run_id=run_id,
                    step_number=step_number,
                    timestamp=datetime.now(),
                    request_json=request_json,
                    screenshot_path=screenshot_path,
                    response_raw=response_text,
                    response_parsed_json=json.dumps({
                        "actions": [
                            {
                                "action": action.action,
                                "action_desc": action.action_desc,
                                "target_bounding_box": {
                                    "top_left": list(action.target_bounding_box.top_left),
                                    "bottom_right": list(action.target_bounding_box.bottom_right)
                                },
                                "input_text": action.input_text,
                                "reasoning": action.reasoning
                            } for action in ai_response.actions
                        ],
                        "signup_completed": ai_response.signup_completed
                    }),
                    tokens_input=usage_info.get('input_tokens') if usage_info else None,
                    tokens_output=usage_info.get('output_tokens') if usage_info else None,
                    latency_ms=latency_ms,
                    success=True,
                    error_message=None,
                    retry_count=retry_count
                )
                
                self.ai_interaction_repository.create_ai_interaction(interaction)
                
                # Emit response received event
                if self.event_listener:
                    response_data = {
                        "success": True,
                        "response": response_text,
                        "parsed_response": json.dumps({
                            "actions": [
                                {
                                    "action": action.action,
                                    "action_desc": action.action_desc,
                                    "target_bounding_box": {
                                        "top_left": list(action.target_bounding_box.top_left),
                                        "bottom_right": list(action.target_bounding_box.bottom_right)
                                    },
                                    "input_text": action.input_text,
                                    "reasoning": action.reasoning
                                } for action in ai_response.actions
                            ],
                            "signup_completed": ai_response.signup_completed
                        }),
                        "tokens_input": usage_info.get('input_tokens') if usage_info else None,
                        "tokens_output": usage_info.get('output_tokens') if usage_info else None,
                        "latency_ms": latency_ms
                    }
                    self.event_listener.on_ai_response_received(run_id, step_number, response_data)
                
                return ai_response
                
            except Exception as e:
                last_exception = e
                
                # Log failed interaction
                interaction = AIInteraction(
                    id=None,
                    run_id=run_id,
                    step_number=step_number,
                    timestamp=datetime.now(),
                    request_json=request_json,
                    screenshot_path=screenshot_path,
                    response_raw=None,
                    response_parsed_json=None,
                    tokens_input=None,
                    tokens_output=None,
                    latency_ms=None,
                    success=False,
                    error_message=str(e),
                    retry_count=retry_count
                )
                
                self.ai_interaction_repository.create_ai_interaction(interaction)
                
                # Emit error response event
                if self.event_listener and retry_count == max_retries:
                    error_response_data = {
                        "success": False,
                        "error_message": str(e),
                        "retry_count": retry_count
                    }
                    self.event_listener.on_ai_response_received(run_id, step_number, error_response_data)
                
                if retry_count < max_retries:
                    continue
        
        # All retries failed
        raise last_exception or Exception("AI interaction failed after all retries")

    def _parse_ai_response(self, response_text: str) -> AIResponse:
        """Parse and validate AI response.

        Args:
            response_text: Raw response from AI model

        Returns:
            Parsed AIResponse

        Raises:
            ValueError: If response format is invalid
        """
        if not response_text:
            raise ValueError("Empty response from AI model")
        
        # Strip markdown code fences if present
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```"):
            # Remove opening fence (```json or ```)
            lines = cleaned_text.split('\n')
            if lines[0].startswith("```"):
                lines = lines[1:]  # Remove first line with ```
            # Remove closing fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned_text = '\n'.join(lines).strip()
        
        if not cleaned_text:
            raise ValueError("Empty response after stripping code fences")
        
        try:
            data = json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            # Log first 200 chars of response for debugging
            preview = cleaned_text[:200] if len(cleaned_text) > 200 else cleaned_text
            raise ValueError(f"Invalid JSON response: {e}. Response preview: {preview!r}")
        
        # Validate required fields
        if "actions" not in data:
            raise ValueError("Response missing 'actions' field")
        if "signup_completed" not in data:
            raise ValueError("Response missing 'signup_completed' field")
        
        if not isinstance(data["actions"], list):
            raise ValueError("'actions' must be a list")
        if not isinstance(data["signup_completed"], bool):
            raise ValueError("'signup_completed' must be a boolean")
        
        # Parse actions
        actions = []
        for i, action_data in enumerate(data["actions"]):
            try:
                action = self._parse_action(action_data)
                actions.append(action)
            except Exception as e:
                raise ValueError(f"Invalid action at index {i}: {e}")
        
        # Validate action count
        if not (1 <= len(actions) <= 12):
            raise ValueError(f"Action count {len(actions)} not in range 1-12")
        
        return AIResponse(
            actions=actions,
            signup_completed=data["signup_completed"],
            latency_ms=0.0  # Will be set by caller
        )

    def _parse_action(self, action_data: dict) -> AIAction:
        """Parse a single action from AI response.

        Args:
            action_data: Action data from AI response

        Returns:
            Parsed AIAction

        Raises:
            ValueError: If action format is invalid
        """
        required_fields = ["action", "action_desc", "target_bounding_box", "reasoning"]
        for field in required_fields:
            if field not in action_data:
                raise ValueError(f"Action missing required field: {field}")
        
        # Validate action type
        valid_actions = [
            "click", "input", "long_press", "scroll_up", "scroll_down", 
            "scroll_left", "scroll_right", "back"
        ]
        if action_data["action"] not in valid_actions:
            raise ValueError(f"Invalid action type: {action_data['action']}")
        
        # Parse bounding box
        bbox_data = action_data["target_bounding_box"]
        if "top_left" not in bbox_data or "bottom_right" not in bbox_data:
            raise ValueError("Bounding box missing top_left or bottom_right")
        
        top_left = tuple(bbox_data["top_left"])
        bottom_right = tuple(bbox_data["bottom_right"])
        
        if len(top_left) != 2 or len(bottom_right) != 2:
            raise ValueError("Bounding box coordinates must be [x, y] pairs")
        
        bounding_box = BoundingBox(
            top_left=top_left,
            bottom_right=bottom_right
        )
        
        # Validate input_text for input actions
        input_text = action_data.get("input_text")
        if action_data["action"] == "input" and input_text is None:
            raise ValueError("Input action requires input_text")
        if action_data["action"] != "input" and input_text is not None:
            raise ValueError("Only input actions can have input_text")
        
        return AIAction(
            action=action_data["action"],
            action_desc=action_data["action_desc"],
            target_bounding_box=bounding_box,
            input_text=input_text,
            reasoning=action_data["reasoning"]
        )