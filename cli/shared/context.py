"""
Application context providing shared dependencies to commands and services.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Determine project root
from utils.paths import find_project_root
_project_root = find_project_root(Path(__file__).resolve().parent)
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.logging_infrastructure import (
    configure_default_logging,
    setup_logging_bridge,
    LogLevel,
    LoggingService
)

# Lazy import to avoid circular dependency
# Config is imported inside _initialize_config() method
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from config.app_config import Config


class ServiceRegistry:
    """Registry for managing service instances."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
    
    def register(self, name: str, service: Any) -> None:
        """Register a service instance."""
        self._services[name] = service
    
    def get(self, name: str) -> Any:
        """Get a service instance."""
        return self._services.get(name)
    
    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services


class ApplicationContext:
    """
    Shared context for application operations.
    
    Provides access to configuration, logging, and shared utilities
    across all CLI commands, GUI components, and services.
    """
    
    def __init__(self, verbose: bool = False, config: Optional['Config'] = None):
        """
        Initialize application context.
        
        Args:
            verbose: Enable verbose logging
            config: Optional Config instance. If None, creates a new one.
        """
        self.verbose = verbose
        self._config: Optional['Config'] = None
        self._root_logger_service: Optional[LoggingService] = None
        self._services = ServiceRegistry()
        self._setup_logging(verbose)
        self._initialize_config(config)
    
    def _setup_logging(self, verbose: bool) -> None:
        """Setup initial logging configuration."""
        log_level = LogLevel.DEBUG if verbose else LogLevel.WARNING
        
        # Configure basic logging first
        # We start with just console logging until config is loaded
        service = configure_default_logging(
            console_level=log_level
        )
        setup_logging_bridge(service, level=log_level.name)
        
        self._root_logger_service = service
        self._log_level = log_level
    
    def _initialize_config(self, config: Optional['Config'] = None) -> None:
        """Initialize configuration and final logging setup.
        
        Args:
            config: Optional Config instance. If None, creates a new one.
        """
        # Lazy import to avoid circular dependency
        from config.app_config import Config
        
        # Find project root using marker files
        api_dir = find_project_root(Path(__file__).resolve().parent)
        
        try:
            # Use provided config or create a new one
            if config is not None:
                self._config = config
            else:
                self._config = Config()
            
            # Setup final logging with file output
            self._setup_final_logging()
            
        except Exception as e:
            logging.critical(f"Failed to initialize Config: {e}", exc_info=True)
            sys.exit(100)
    
    def _setup_final_logging(self) -> None:
        """Setup final logging with file output."""
        if not self._config:
            return
            
        # Refine logging config now that we have paths
        log_file_base = Path(self._config.OUTPUT_DATA_DIR or str(_project_root))
        log_file_path = log_file_base / "logs" / "cli" / f"cli_{self._config.LOG_FILE_NAME}"
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Re-configure default logging with file
        self._root_logger_service = configure_default_logging(
            console_level=self._log_level,
            log_file=log_file_path,
            file_level=LogLevel.DEBUG
        )
        setup_logging_bridge(self._root_logger_service, level=self._log_level.name)
        
    
    @property
    def config(self) -> 'Config':
        """Get the configuration instance."""
        if not self._config:
            raise RuntimeError("Configuration not initialized")
        return self._config
    
    @property
    def services(self) -> ServiceRegistry:
        """Get the service registry."""
        return self._services
    
    def get_api_dir(self) -> str:
        """Get the API directory path."""
        return str(_project_root)
    
    def get_project_root(self) -> str:
        """Get the project root directory."""
        return str(_project_root)
