"""UI dump validation module for crawl step guardrails.

Provides:
- UIDumpValidator / UIDumpValidationResult for UI dump validation gate
- StepSkipReason enum for skip reason tracking

Target-app identity (whether the crawl drifted to the wrong foreground app)
is Target Recovery's job, handled once in
``crawler_agent.tools.ui.provider.AndroidStateProvider``, not here.
"""

import enum
import logging
import xml.etree.ElementTree as ET
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class StepSkipReason(enum.Enum):
    """Reasons a crawl step may be skipped instead of proceeding to DECIDE/EXECUTE."""

    INVALID_UI_DUMP = "invalid_ui_dump"


@dataclass
class UIDumpValidationResult:
    """Result of validating a UI dump before the decision layer processes it.

    Per D-03: UI dumps must be both parseable and non-empty before reaching
    the AI decision layer. Invalid dumps are retried once (D-04) and then
    the step is marked SKIPPED — the run never aborts on a bad dump.
    """

    is_valid: bool
    is_parseable: bool
    element_count: int
    error: str | None = None


class UIDumpValidator:
    """Validates UI tree dumps before the decision layer processes them.

    Implements D-03 (parseable AND non-empty) and D-04 (retry once, then skip).
    Never raises exceptions — always returns a UIDumpValidationResult. Invalid
    UI data should cause the step to be skipped, not the run to abort.
    """

    def validate(self, ui_data: Any) -> UIDumpValidationResult:
        """Validate raw UI data for parseability and non-emptiness.

        Accepts lists (a11y tree), dicts (state with a11y_tree key), XML strings,
        or None. Returns a result indicating whether the data is safe for the
        decision layer.

        Args:
            ui_data: Raw UI data from DroidRun state. Can be a list of a11y
                elements, a dict with an 'a11y_tree' or 'elements' key, an XML
                string, or None/empty values indicating a failed dump.

        Returns:
            UIDumpValidationResult with is_valid, is_parseable, element_count,
            and optional error description.
        """
        # None or falsy — not parseable at all
        if ui_data is None:
            return UIDumpValidationResult(
                is_valid=False,
                is_parseable=False,
                element_count=0,
                error="ui_data_is_none",
            )

        # String — try XML parsing
        if isinstance(ui_data, str):
            return self._validate_xml(ui_data)

        # List — check it's iterable and has elements
        if isinstance(ui_data, list):
            if len(ui_data) == 0:
                return UIDumpValidationResult(
                    is_valid=False,
                    is_parseable=True,
                    element_count=0,
                    error="empty_ui_dump",
                )
            return UIDumpValidationResult(
                is_valid=True,
                is_parseable=True,
                element_count=len(ui_data),
            )

        # Dict — look for a11y_tree or elements key
        if isinstance(ui_data, dict):
            # Try a11y_tree first (DroidRun convention)
            a11y = ui_data.get("a11y_tree")
            if a11y is not None:
                return self.validate(a11y)

            # Try elements key (alternate convention)
            elements = ui_data.get("elements")
            if elements is not None:
                return self.validate(elements)

            # Dict without recognizable key — treat as single element if non-empty
            if len(ui_data) > 0:
                return UIDumpValidationResult(
                    is_valid=True,
                    is_parseable=True,
                    element_count=1,
                )
            return UIDumpValidationResult(
                is_valid=False,
                is_parseable=True,
                element_count=0,
                error="empty_ui_dump",
            )

        # Any other type — check if it's iterable
        try:
            count = sum(1 for _ in ui_data)
            if count == 0:
                return UIDumpValidationResult(
                    is_valid=False,
                    is_parseable=True,
                    element_count=0,
                    error="empty_ui_dump",
                )
            return UIDumpValidationResult(
                is_valid=True,
                is_parseable=True,
                element_count=count,
            )
        except TypeError:
            return UIDumpValidationResult(
                is_valid=False,
                is_parseable=False,
                element_count=0,
                error="ui_data_unparseable_type",
            )

    def _validate_xml(self, xml_string: str) -> UIDumpValidationResult:
        """Validate an XML string UI dump.

        Empty string is treated as not parseable. Malformed XML returns
        is_parseable=False. Valid XML with no child elements returns
        is_valid=False with element_count=0.
        """
        if not xml_string.strip():
            return UIDumpValidationResult(
                is_valid=False,
                is_parseable=False,
                element_count=0,
                error="empty_xml_string",
            )

        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            return UIDumpValidationResult(
                is_valid=False,
                is_parseable=False,
                element_count=0,
                error=f"xml_parse_error: {e}",
            )

        # Count child elements (direct children of root)
        child_count = len(root)
        if child_count == 0:
            return UIDumpValidationResult(
                is_valid=False,
                is_parseable=True,
                element_count=0,
                error="empty_ui_dump",
            )

        return UIDumpValidationResult(
            is_valid=True,
            is_parseable=True,
            element_count=child_count,
        )

    async def validate_ui_dump_with_retry(
        self,
        ui_data_getter: Callable[[], Awaitable[Any]],
        max_retries: int = 1,
    ) -> UIDumpValidationResult:
        """Validate UI dump with one retry for transient failures (per D-04).

        Calls ui_data_getter to obtain fresh data, validates it, and if
        invalid with retries remaining, calls the getter again (one retry
        for transient failures like stale ADB state). If still invalid
        after retry, returns the invalid result. Never raises.

        Args:
            ui_data_getter: Callable that returns fresh UI data when invoked.
            max_retries: Number of retry attempts. Defaults to 1 per D-04.

        Returns:
            UIDumpValidationResult for the final validation attempt.
        """
        result = self.validate(await ui_data_getter())

        if result.is_valid:
            return result

        retries = 0
        while retries < max_retries and not result.is_valid:
            logger.info(
                f"UI dump validation failed ({result.error}), "
                f"retrying ({retries + 1}/{max_retries})"
            )
            result = self.validate(await ui_data_getter())
            retries += 1

        if not result.is_valid:
            logger.warning(
                f"UI dump validation still invalid after {max_retries} "
                f"retries: {result.error}"
            )

        return result
