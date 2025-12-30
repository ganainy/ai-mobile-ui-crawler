# ui_state_handler.py - UI State Management Handler
# Handles dynamic UI state and logic, separated from component creation

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QThread, Signal, QObject
from PySide6.QtWidgets import QGroupBox, QLabel, QApplication, QWidget

from config.app_config import Config
from domain.providers.registry import ProviderRegistry
from domain.providers.enums import AIProvider


class ModelFetchWorker(QThread):
    """Background worker thread to fetch models from AI providers without blocking UI."""
    
    # Signal emitted when models are fetched successfully
    models_fetched = Signal(str, list)  # (provider_name, models_list)
    # Signal emitted when fetch fails
    fetch_failed = Signal(str, str)  # (provider_name, error_message)
    
    def __init__(self, provider_name: str, free_only: bool = False, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.provider_name = provider_name
        self.free_only = free_only
        self._is_cancelled = False
    
    def cancel(self):
        """Request cancellation of the fetch operation."""
        self._is_cancelled = True
    
    def run(self):
        """Fetch models in background thread."""
        try:
            if self._is_cancelled:
                return
            
            # Get provider strategy
            strategy = ProviderRegistry.get_by_name(self.provider_name)
            if not strategy:
                self.fetch_failed.emit(self.provider_name, f"Unknown provider: {self.provider_name}")
                return
            
            if self._is_cancelled:
                return
            
            # Create a fresh config object for this thread (SQLite is thread-local)
            try:
                config = Config()
                if self.free_only:
                    config.set("OPENROUTER_SHOW_FREE_ONLY", True)
            except Exception as e:
                self.fetch_failed.emit(self.provider_name, f"Config error: {e}")
                return
            
            if self._is_cancelled:
                return
            
            # Fetch models (this is the blocking network call)
            models = strategy.get_models(config)
            
            if self._is_cancelled:
                return
            
            if models:
                self.models_fetched.emit(self.provider_name, models)
            else:
                self.models_fetched.emit(self.provider_name, [])
                
        except Exception as e:
            if not self._is_cancelled:
                logging.warning(f"Background model fetch failed for {self.provider_name}: {e}")
                self.fetch_failed.emit(self.provider_name, str(e))


class UIStateHandler:
    """Handles dynamic UI state management and logic."""
    
    def __init__(self, main_controller: Any, config_handler: Any, config_widgets: Dict[str, Any], ui_groups: Dict[str, QWidget]):
        """
        Initialize the UI state handler.
        
        Args:
            main_controller: The main CrawlerControllerWindow instance
            config_handler: The ConfigManager instance
            config_widgets: Dictionary of config UI widgets
            ui_groups: Dictionary of UI group widgets
        """
        self.main_controller = main_controller
        self.config_handler = config_handler
        self.config_widgets = config_widgets
        self.ui_groups = ui_groups
        self.config: Config = main_controller.config
        
        # Track active model fetch worker to cancel previous fetches
        self._model_fetch_worker: Optional[ModelFetchWorker] = None
        # Track current provider being fetched to avoid duplicate updates
        self._current_fetching_provider: Optional[str] = None


    def _configure_image_context_for_provider(
        self, strategy, config, capabilities, model_dropdown, no_selection_label
    ):
        """Configure image context UI based on provider strategy and capabilities."""
        # Always keep the checkbox enabled
        self.config_widgets["CONTEXT_SOURCE_IMAGE"].setEnabled(True)
        
        # Always show the fixed warning message
        if "IMAGE_CONTEXT_WARNING" in self.config_widgets:
            warning_text = "⚠️ No images will be sent if selected model doesn't support images"
            self.config_widgets["IMAGE_CONTEXT_WARNING"].setText(warning_text)
            self.config_widgets["IMAGE_CONTEXT_WARNING"].setVisible(True)
        
        # Set tooltip
        from ui.strings import IMAGE_CONTEXT_ENABLED_TOOLTIP
        self.config_widgets["CONTEXT_SOURCE_IMAGE"].setToolTip(IMAGE_CONTEXT_ENABLED_TOOLTIP)
        self.config_widgets["CONTEXT_SOURCE_IMAGE"].setStyleSheet("")
        
        # Update preprocessing visibility based on current checked state
        try:
            current_checked = self.config_widgets["CONTEXT_SOURCE_IMAGE"].isChecked()
            self._update_image_preprocessing_visibility(current_checked)
        except Exception as e:
            pass

    def _setup_model_image_context_handler(
        self, strategy, config, model_dropdown, no_selection_label
    ):
        """Set up model-specific image context handling with model change listener.
        
        This handler no longer disables the checkbox, but maintains the connection
        for potential future use.
        """
        def _on_model_changed(name: str):
            try:
                if "CONTEXT_SOURCE_IMAGE" not in self.config_widgets:
                    return
                
                # Always keep checkbox enabled
                self.config_widgets["CONTEXT_SOURCE_IMAGE"].setEnabled(True)
                
                # Always show the fixed warning
                if "IMAGE_CONTEXT_WARNING" in self.config_widgets:
                    warning_text = "⚠️ No images will be sent if selected model doesn't support images"
                    self.config_widgets["IMAGE_CONTEXT_WARNING"].setText(warning_text)
                    self.config_widgets["IMAGE_CONTEXT_WARNING"].setVisible(True)
                
                # Update preprocessing visibility based on checkbox state
                try:
                    current_checked = self.config_widgets["CONTEXT_SOURCE_IMAGE"].isChecked()
                    self._update_image_preprocessing_visibility(current_checked)
                except Exception as e:
                    pass
            except Exception as e:
                pass
        
        model_dropdown.currentTextChanged.connect(_on_model_changed)
        
        # Immediately validate the current model
        current_model = model_dropdown.currentText()
        if current_model:
            _on_model_changed(current_model)

    def _update_model_types(self, provider: str) -> None:
        """Update the model types based on the selected AI provider using provider strategy.
        
        For providers that require network requests (like Ollama), this uses async fetching
        to prevent UI freezes. A background worker thread fetches the models while the UI
        remains responsive.
        """
        model_dropdown = self.config_widgets["DEFAULT_MODEL_TYPE"]
        # Capture the current selection to restore it after repopulating
        previous_text = model_dropdown.currentText()

        # Block signals to prevent auto-save from triggering with an empty value
        model_dropdown.blockSignals(True)

        model_dropdown.clear()

        # Always start with an explicit no-selection placeholder
        from ui.strings import NO_MODEL_SELECTED
        NO_SELECTION_LABEL = NO_MODEL_SELECTED
        try:
            model_dropdown.addItem(NO_SELECTION_LABEL)
        except Exception:
            # Fallback: ensure dropdown has at least one item
            model_dropdown.addItem(NO_MODEL_SELECTED)

        # Get provider strategy
        strategy = ProviderRegistry.get_by_name(provider)
        if not strategy:
            logging.warning(f"Unknown provider: {provider}")
            model_dropdown.blockSignals(False)
            return
        
        # Get provider enum for type checking
        provider_enum = AIProvider.from_string(provider) if AIProvider.is_valid(provider) else None
        
        # Get provider capabilities
        capabilities = strategy.get_capabilities()
        
        # Get config for provider methods
        try:
            from config.app_config import Config
            config = Config()
        except Exception:
            logging.warning("Could not create config for provider strategy")
            model_dropdown.blockSignals(False)
            return

        # Check free-only filter state from the config object
        free_only = False
        if "OPENROUTER_SHOW_FREE_ONLY" in self.config_widgets:
            free_only = config.get("OPENROUTER_SHOW_FREE_ONLY", False)
            if provider_enum == AIProvider.OPENROUTER:
                config.set("OPENROUTER_SHOW_FREE_ONLY", free_only)
        
        # Check vision-only filter state
        vision_only = False
        if "SHOW_VISION_ONLY" in self.config_widgets:
            vision_only = self.config_widgets["SHOW_VISION_ONLY"].isChecked()
        
        # Store strategy and config for vision filtering
        self._current_strategy = strategy
        self._current_config = config
        self._vision_only = vision_only
        
        # Cancel any existing fetch worker
        if self._model_fetch_worker is not None:
            try:
                self._model_fetch_worker.cancel()
                self._model_fetch_worker.wait(500)  # Wait up to 500ms for clean shutdown
            except Exception:
                pass
            self._model_fetch_worker = None
        
        # For Ollama provider, use async fetching to prevent UI freeze
        # Ollama's get_models() makes HTTP requests that can block
        if provider_enum == AIProvider.OLLAMA:
            # Add a loading indicator
            model_dropdown.addItem("Loading models...")
            model_dropdown.blockSignals(False)
            
            # Store context for later use
            self._current_fetching_provider = provider
            self._previous_model_selection = previous_text
            self._no_selection_label = NO_SELECTION_LABEL
            
            # Start background worker
            self._model_fetch_worker = ModelFetchWorker(provider, free_only, parent=None)
            self._model_fetch_worker.models_fetched.connect(self._on_models_fetched)
            self._model_fetch_worker.fetch_failed.connect(self._on_model_fetch_failed)
            self._model_fetch_worker.start()
            
            # Configure image context based on provider capabilities (synchronous part)
            if "CONTEXT_SOURCE_IMAGE" in self.config_widgets:
                self._configure_image_context_for_provider(
                    strategy, config, capabilities, model_dropdown, NO_SELECTION_LABEL
                )
            return
        
        # For other providers (Gemini, OpenRouter), use synchronous fetching
        # These are typically fast (cached or simple API calls)
        try:
            models = strategy.get_models(config)
            if models:
                # Apply vision-only filter if enabled
                if vision_only:
                    models = [m for m in models if strategy.supports_image_context(config, m)]
                
                # Process models in batches to avoid blocking UI thread
                batch_size = 50
                for i in range(0, len(models), batch_size):
                    batch = models[i:i + batch_size]
                    model_dropdown.addItems(batch)
                    QApplication.processEvents()
        except Exception as e:
            logging.warning(f"Failed to get models from provider strategy: {e}")
        
        # Restore previous selection if available
        try:
            if previous_text:
                idx = model_dropdown.findText(previous_text)
                if idx >= 0:
                    model_dropdown.setCurrentIndex(idx)
        except Exception:
            pass

        # Configure image context based on provider capabilities
        if "CONTEXT_SOURCE_IMAGE" in self.config_widgets:
            self._configure_image_context_for_provider(
                strategy, config, capabilities, model_dropdown, NO_SELECTION_LABEL
            )

        # Unblock signals after updating
        model_dropdown.blockSignals(False)
    
    def _on_models_fetched(self, provider_name: str, models: List[str]) -> None:
        """Handle successful async model fetch.
        
        This slot is called when the background worker finishes fetching models.
        Updates the dropdown with the fetched models on the main UI thread.
        """
        # Verify this is still the provider we're waiting for
        if provider_name != self._current_fetching_provider:
            return
        
        model_dropdown = self.config_widgets.get("DEFAULT_MODEL_TYPE")
        if not model_dropdown:
            return
        
        model_dropdown.blockSignals(True)
        
        # Clear and repopulate
        model_dropdown.clear()
        
        from ui.strings import NO_MODEL_SELECTED
        model_dropdown.addItem(self._no_selection_label or NO_MODEL_SELECTED)
        
        if models:
            # Apply vision-only filter if enabled
            vision_only = getattr(self, '_vision_only', False)
            if vision_only:
                strategy = getattr(self, '_current_strategy', None)
                config = getattr(self, '_current_config', None)
                if strategy and config:
                    models = [m for m in models if strategy.supports_image_context(config, m)]
            
            # Add models in batches
            batch_size = 50
            for i in range(0, len(models), batch_size):
                batch = models[i:i + batch_size]
                model_dropdown.addItems(batch)
                QApplication.processEvents()
            
            logging.info(f"Loaded {len(models)} models for {provider_name}")
        else:
            logging.warning(f"No models found for {provider_name}")
        
        # Restore previous selection if available
        previous_text = getattr(self, '_previous_model_selection', None)
        if previous_text:
            idx = model_dropdown.findText(previous_text)
            if idx >= 0:
                model_dropdown.setCurrentIndex(idx)
        
        model_dropdown.blockSignals(False)
        self._current_fetching_provider = None
        self._model_fetch_worker = None
    
    def _on_model_fetch_failed(self, provider_name: str, error_message: str) -> None:
        """Handle failed async model fetch.
        
        This slot is called when the background worker fails to fetch models.
        Shows an error state in the dropdown.
        """
        # Verify this is still the provider we're waiting for
        if provider_name != self._current_fetching_provider:
            return
        
        model_dropdown = self.config_widgets.get("DEFAULT_MODEL_TYPE")
        if not model_dropdown:
            return
        
        model_dropdown.blockSignals(True)
        
        # Clear and show error state
        model_dropdown.clear()
        
        from ui.strings import NO_MODEL_SELECTED
        model_dropdown.addItem(self._no_selection_label or NO_MODEL_SELECTED)
        model_dropdown.addItem(f"⚠️ Failed to load: {error_message[:30]}...")
        
        logging.warning(f"Failed to fetch models for {provider_name}: {error_message}")
        
        model_dropdown.blockSignals(False)
        self._current_fetching_provider = None
        self._model_fetch_worker = None

    def _add_image_context_warning(self, provider: str, capabilities: Dict[str, Any]) -> None:
        """Add visual warning when image context is auto-disabled."""
        try:
            payload_limit = capabilities.get("payload_max_size_kb", 150)
            warning_msg = f"⚠️ IMAGE CONTEXT AUTO-DISABLED: {provider} has strict payload limits ({payload_limit}KB max). Image context automatically disabled to prevent API errors."

            # Log the warning
            logging.warning(
                f"Image context auto-disabled for {provider} due to payload limits"
            )

            # Try to show warning in UI if main controller is available
            try:
                # Get the main window instance if it exists
                app = QApplication.instance()
                if app and isinstance(app, QApplication):
                    for widget in app.topLevelWidgets():
                        if isinstance(widget, type(self.main_controller)):
                            widget.log_message(warning_msg, "orange")
                            break
            except Exception as e:
                pass
        except Exception as e:
            logging.error(f"Error adding image context warning: {e}")

    def _update_image_preprocessing_visibility(self, enabled: bool):
        """
        Update visibility of image preprocessing options based on Enable Image Context state.
        
        Args:
            enabled: Whether image context is enabled
        """
        if 'image_preprocessing_group' not in self.ui_groups:
            return
        
        image_prep_group = self.ui_groups['image_preprocessing_group']
        if not hasattr(image_prep_group, 'preprocessing_widgets') or not hasattr(image_prep_group, 'preprocessing_labels'):
            return
        
        # Update visibility of all preprocessing widgets and labels
        for widget in image_prep_group.preprocessing_widgets:
            if widget:
                widget.setVisible(enabled)
        
        for label in image_prep_group.preprocessing_labels:
            if label:
                label.setVisible(enabled)

    def _refresh_models(self) -> None:
        """Generic refresh function that works for all AI providers.
        
        For Ollama, uses async worker to prevent UI freezes.
        For other providers, uses synchronous refresh with cache support.
        """
        try:
            current_provider_name = self.config_widgets["AI_PROVIDER"].currentText()
            self.main_controller.log_message(
                f"Starting {current_provider_name} model refresh...", "blue"
            )
            
            provider = ProviderRegistry.get_by_name(current_provider_name)
            if not provider:
                error_msg = f"Unknown provider: {current_provider_name}"
                logging.error(error_msg)
                self.main_controller.log_message(error_msg, "red")
                return
            
            # Get provider enum
            provider_enum = AIProvider.from_string(current_provider_name) if AIProvider.is_valid(current_provider_name) else None
            
            # For Ollama, use async refresh to prevent UI freeze
            if provider_enum == AIProvider.OLLAMA:
                self._refresh_models_async(current_provider_name)
                return
            
            # For other providers, use synchronous refresh
            try:
                self.main_controller.log_message(
                    f"Refreshing {current_provider_name} models...", "blue"
                )
                
                success, cache_path = provider.refresh_models(
                    config=self.config_handler.config,
                    wait_for_completion=True
                )
                
                if success:
                    try:
                        models = provider.get_models(self.config_handler.config)
                        model_count = len(models) if models else 0
                        source = "Downloaded from API"
                        final_message = f"{current_provider_name} models refreshed successfully. Found {model_count} models. {source}"
                    except Exception as e:
                        source = "Downloaded from API"
                        final_message = f"{current_provider_name} models refreshed successfully. {source}"
                    
                    self.main_controller.log_message(final_message, "green")
                    self._update_model_types(current_provider_name)
                else:
                    error_message = f"{current_provider_name} refresh failed"
                    if cache_path:
                        error_message += f" (cache path: {cache_path})"
                    else:
                        error_message += ". Check network connection and API key."
                    self.main_controller.log_message(error_message, "orange")
            
            except RuntimeError as e:
                error_str = str(e)
                try:
                    models = provider.get_models(self.config_handler.config)
                    if models:
                        model_count = len(models) if models else 0
                        source = "Loaded from cache"
                        final_message = f"{current_provider_name} models loaded successfully. Found {model_count} models. {source}"
                        self.main_controller.log_message(final_message, "green")
                        self._update_model_types(current_provider_name)
                        return
                except Exception:
                    pass
                
                if "timed out" in error_str.lower():
                    error_msg = f"{current_provider_name} model refresh timed out. {error_str}"
                else:
                    error_msg = f"{current_provider_name} model refresh failed: {error_str}"
                logging.error(error_msg, exc_info=True)
                self.main_controller.log_message(error_msg, "orange")
            except Exception as e:
                try:
                    models = provider.get_models(self.config_handler.config)
                    if models:
                        model_count = len(models) if models else 0
                        source = "Loaded from cache"
                        final_message = f"{current_provider_name} models loaded successfully. Found {model_count} models. {source}"
                        self.main_controller.log_message(final_message, "green")
                        self._update_model_types(current_provider_name)
                        return
                except Exception:
                    pass
                
                error_msg = f"{current_provider_name} model refresh failed: {str(e)}"
                logging.error(error_msg, exc_info=True)
                self.main_controller.log_message(error_msg, "orange")
        
        except Exception as e:
            logging.error(f"Error starting refresh: {e}", exc_info=True)
            try:
                self.main_controller.log_message(
                    f"Failed to start refresh: {e}", "orange"
                )
            except Exception:
                pass
    
    def _refresh_models_async(self, provider_name: str) -> None:
        """Refresh models asynchronously using a background worker.
        
        Used for providers like Ollama that require network requests.
        """
        # Cancel any existing fetch worker
        if self._model_fetch_worker is not None:
            try:
                self._model_fetch_worker.cancel()
                self._model_fetch_worker.wait(500)
            except Exception:
                pass
            self._model_fetch_worker = None
        
        # Update dropdown to show loading state
        model_dropdown = self.config_widgets.get("DEFAULT_MODEL_TYPE")
        if model_dropdown:
            model_dropdown.blockSignals(True)
            # Remember current selection
            previous_text = model_dropdown.currentText()
            self._previous_model_selection = previous_text
            
            model_dropdown.clear()
            from ui.strings import NO_MODEL_SELECTED
            self._no_selection_label = NO_MODEL_SELECTED
            model_dropdown.addItem(NO_MODEL_SELECTED)
            model_dropdown.addItem("Refreshing models...")
            model_dropdown.blockSignals(False)
        
        # Store context
        self._current_fetching_provider = provider_name
        
        # Get free-only preference
        free_only = False
        if "OPENROUTER_SHOW_FREE_ONLY" in self.config_widgets:
            try:
                from config.app_config import Config
                config = Config()
                free_only = config.get("OPENROUTER_SHOW_FREE_ONLY", False)
            except Exception:
                pass
        
        # Start background worker
        self._model_fetch_worker = ModelFetchWorker(provider_name, free_only, parent=None)
        self._model_fetch_worker.models_fetched.connect(self._on_refresh_models_fetched)
        self._model_fetch_worker.fetch_failed.connect(self._on_refresh_model_fetch_failed)
        self._model_fetch_worker.start()
        
        self.main_controller.log_message(
            f"{provider_name} models refresh started in background...", "blue"
        )
    
    def _on_refresh_models_fetched(self, provider_name: str, models: List[str]) -> None:
        """Handle successful async refresh."""
        if provider_name != self._current_fetching_provider:
            return
        
        model_count = len(models) if models else 0
        self.main_controller.log_message(
            f"{provider_name} models refreshed successfully. Found {model_count} models.", "green"
        )
        
        # Update the dropdown via the standard handler
        self._on_models_fetched(provider_name, models)
    
    def _on_refresh_model_fetch_failed(self, provider_name: str, error_message: str) -> None:
        """Handle failed async refresh."""
        if provider_name != self._current_fetching_provider:
            return
        
        self.main_controller.log_message(
            f"{provider_name} model refresh failed: {error_message}", "orange"
        )
        
        # Update the dropdown via the standard handler
        self._on_model_fetch_failed(provider_name, error_message)

