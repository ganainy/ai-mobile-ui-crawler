"""Context-aware form input dictionary for matching UI fields to appropriate test values."""

import logging
import re
from typing import Any

from mobile_crawler.config.config_manager import ConfigManager

logger = logging.getLogger("crawler_agent")


class ContextAwareInputDictionary:
    """Matches form input fields to contextually relevant mock data or credentials."""

    def __init__(self, config_manager: ConfigManager | None = None):
        """Initialize the input dictionary with configuration.

        Args:
            config_manager: Configuration manager to load custom test values.
        """
        self.config_manager = config_manager

        # Load credentials with config fallback
        self.values = {
            "email": self._get_config_val("test_email", "test_user@example.com"),
            "phone": self._get_config_val("test_phone", "15555555555"),
            "username": self._get_config_val("test_username", "testuser"),
            "password": self._get_config_val("test_password", "Password123!"),
            "address": self._get_config_val("test_address", "123 Test St"),
            "city": "Test City",
            "zip": "12345",
            "search": "test",
            "generic": "test input"
        }

        # Regex patterns for matching field identifiers
        self.patterns = {
            "email": re.compile(r"(?:email|mail|address_email)", re.IGNORECASE),
            "phone": re.compile(r"(?:phone|mobile|\btel\b|contact|number)", re.IGNORECASE),
            "password": re.compile(r"(?:pass|pwd|code|\bpin\b|security)", re.IGNORECASE),
            "address": re.compile(r"(?:address|street|location)", re.IGNORECASE),
            "city": re.compile(r"(?:city|town|state|province)", re.IGNORECASE),
            "zip": re.compile(r"(?:zip|postal|postcode)", re.IGNORECASE),
            "search": re.compile(r"(?:search|query|find|filter)", re.IGNORECASE),
            "username": re.compile(r"(?:user|login|\bid\b|name|first|last|profile)", re.IGNORECASE)
        }

    def _get_config_val(self, key: str, default: str) -> str:
        if self.config_manager:
            return str(self.config_manager.get(key, default) or default)
        return default

    def get_suggested_input(self, element: dict[str, Any]) -> str:
        """Analyze a text input UI element and suggest the best value to fill it with.

        Args:
            element: Formatted UI element dictionary containing resourceId, text, className, etc.

        Returns:
            Best synthetic test string value to write into the element.
        """
        resource_id = element.get("resourceId", "") or ""
        text = element.get("text", "") or ""
        class_name = element.get("className", "") or ""

        # Check in order of specificity
        combined_identifiers = f"{resource_id} {text} {class_name}"

        for field_type, pattern in self.patterns.items():
            if pattern.search(combined_identifiers):
                suggested = self.values.get(field_type, self.values["generic"])
                logger.debug(
                    f"InputDictionary: Matched element (id={resource_id[:15]}, text={text[:15]}) "
                    f"to field type '{field_type}' -> '{suggested}'"
                )
                return suggested

        logger.debug(
            f"InputDictionary: No match for element (id={resource_id[:15]}, text={text[:15]}) "
            f"-> using generic '{self.values['generic']}'"
        )
        return self.values["generic"]
