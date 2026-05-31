"""OmniParser client for vision-based UI parsing in DroidRun."""

import base64
import io
import logging
import os
from enum import Enum
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class OmniParserBackend(Enum):
    REPLICATE = "replicate"
    LOCAL = "local"


class OmniParserClient:
    """Client for OmniParser vision-based UI parsing.

    Supports two backends:
    - Replicate API (default): Pay-per-call, no GPU needed
    - Local server: Faster, requires GPU setup

    Example element from parse result:
    {
        "type": "text",  # or "icon"
        "bbox": [0.05, 0.85, 0.95, 0.92],  # [x1, y1, x2, y2] in ratios
        "interactivity": True,
        "content": "In den Warenkorb"
    }
    """

    def __init__(
        self,
        backend: str = "replicate",
        api_key: Optional[str] = None,
        local_url: str = "http://localhost:8000",
        box_threshold: float = 0.05,
    ):
        """Initialize OmniParser client.

        Args:
            backend: "replicate" or "local"
            api_key: API key for Replicate (or set REPLICATE_API_KEY env var)
            local_url: URL for local OmniParser server
            box_threshold: Minimum confidence threshold for element detection
        """
        self.backend = OmniParserBackend(backend)
        self._api_key = api_key or os.environ.get("REPLICATE_API_KEY")
        self.local_url = local_url
        self.box_threshold = box_threshold
        logger.debug(
            f"OmniParser initialized: backend={backend}, has_api_key={bool(self._api_key)}"
        )

    def parse(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """Parse screenshot using OmniParser.

        Args:
            image_bytes: Screenshot image data

        Returns:
            List of UI elements with bounding boxes and descriptions
        """
        if self.backend == OmniParserBackend.LOCAL:
            return self._parse_local(image_bytes)
        else:
            return self._parse_replicate(image_bytes)

    def _parse_replicate(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """Parse using Replicate API.

        Args:
            image_bytes: Screenshot image data

        Returns:
            List of UI elements
        """
        import tempfile
        import os

        try:
            import replicate
        except ImportError:
            logger.error("replicate package not installed: pip install replicate")
            raise ImportError("replicate package required: pip install replicate")

        if not self._api_key:
            raise ValueError("Replicate API key not configured. Set REPLICATE_API_KEY env var.")

        # Debug: check image format
        logger.debug(f"Image bytes: {len(image_bytes)} bytes, header: {image_bytes[:20]}")

        # Set environment variable for the new Replicate client
        os.environ["REPLICATE_API_TOKEN"] = self._api_key

        try:
            # Validate image with Pillow first
            try:
                from PIL import Image
                import io

                img = Image.open(io.BytesIO(image_bytes))
                logger.debug(
                    f"PIL detected format: {img.format}, mode: {img.mode}, size: {img.size}"
                )
                # Convert to RGB JPEG
                if img.mode != "RGB":
                    img = img.convert("RGB")
                output = io.BytesIO()
                img.save(output, format="JPEG", quality=95)
                image_bytes = output.getvalue()
                logger.debug(f"Converted to JPEG: {len(image_bytes)} bytes")
            except Exception as img_err:
                logger.warning(f"Image validation/conversion failed: {img_err}")

            # Write to a proper temp file with correct extension
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name

            logger.debug(f"Temp file: {tmp_path}, size: {os.path.getsize(tmp_path)}")

            try:
                # Use new Replicate client API with file path
                client = replicate.Client()

                logger.debug("About to call client.run()")
                try:
                    output = client.run(
                        "microsoft/omniparser-v2:49cf3d41b8d3aca1360514e83be4c97131ce8f0d99abfc365526d8384caa88df",
                        input={
                            "image": open(tmp_path, "rb"),
                            "box_threshold": self.box_threshold,
                        },
                    )
                except Exception as run_err:
                    logger.error(f"client.run() failed: {run_err}")
                    raise

                logger.debug(f"client.run() succeeded, output type: {type(output)}")

                # Parse output - depends on model output format
                logger.debug(f"Replicate output type: {type(output)}")
                logger.debug(f"Replicate output: {str(output)[:500]}")

                if output is None:
                    logger.warning("Replicate returned None")
                    return []

                # Handle the dict response format from OmniParser
                if isinstance(output, dict):
                    # OmniParser v2 returns {"elements": "...", "img": "..."}
                    try:
                        elements_raw = output.get("elements")
                    except Exception as e:
                        logger.error(f"Error getting elements from output: {e}")
                        return []

                    logger.debug(
                        f"elements_raw type: {type(elements_raw)}, value: {str(elements_raw)[:200] if elements_raw else 'empty'}"
                    )

                    valid_elements = []

                    if elements_raw is None:
                        logger.warning("OmniParser returned None for elements")
                        return []

                    if not elements_raw:
                        logger.warning("OmniParser returned empty elements string")
                        return []

                    if isinstance(elements_raw, str) and elements_raw:
                        import ast
                        import re

                        # Split on record boundaries: "icon N: {" starts each record.
                        # Using a lookahead so the delimiter is not consumed.
                        record_pattern = re.compile(r"(?=icon \d+: \{)")
                        records = record_pattern.split(elements_raw)

                        if not any(record.strip() for record in records):
                            logger.warning(f"No icon matches found in: {elements_raw[:300]}")
                            return []

                        for record in records:
                            record = record.strip()
                            if not record:
                                continue
                            # Extract the dict portion after "icon N: "
                            brace_start = record.find("{")
                            if brace_start == -1:
                                continue
                            dict_str = record[brace_start:]
                            # Ensure the string is complete (ends with '}')
                            # Drop truncated last records from Replicate response
                            if not dict_str.rstrip().endswith("}"):
                                logger.debug(
                                    "Dropping truncated OmniParser element: %s",
                                    dict_str[:80],
                                )
                                continue
                            try:
                                el = ast.literal_eval(dict_str)
                                if isinstance(el, dict) and "bbox" in el:
                                    valid_elements.append(el)
                            except (ValueError, SyntaxError) as e:
                                logger.debug("Failed to parse element: %s", e)
                                continue

                    logger.debug(f"Valid elements parsed: {len(valid_elements)}")
                    if valid_elements:
                        logger.debug(f"First valid element: {valid_elements[0]}")

                    return valid_elements if valid_elements else []
                elif isinstance(output, list):
                    return output
                elif isinstance(output, str):
                    # JSON string - try to parse it
                    try:
                        import json

                        parsed = json.loads(output)
                        if isinstance(parsed, dict):
                            return parsed.get("elements", parsed.get("parsed_content", []))
                        elif isinstance(parsed, list):
                            return parsed
                    except Exception:
                        pass
                    return []
                else:
                    logger.warning(f"Unexpected Replicate output type: {type(output)}")
                    return []
            finally:
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Replicate API error: {e}")
            raise RuntimeError(f"OmniParser Replicate error: {e}")

    def _parse_local(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """Parse using local OmniParser server.

        Args:
            image_bytes: Screenshot image data

        Returns:
            List of UI elements
        """
        import requests

        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        try:
            response = requests.post(
                f"{self.local_url}/parse",
                json={
                    "base64_image": b64_image,
                    "box_threshold": self.box_threshold,
                },
                timeout=30,
            )

            if response.status_code != 200:
                raise RuntimeError(f"Local OmniParser error: {response.status_code}")

            return response.json().get("elements", [])

        except requests.exceptions.RequestException as e:
            logger.error(f"Local OmniParser connection error: {e}")
            raise

    def is_available(self) -> bool:
        """Check if OmniParser is available (local server or API key configured).

        Returns:
            True if backend is ready to use
        """
        if self.backend == OmniParserBackend.REPLICATE:
            has_key = bool(self._api_key)
            logger.debug(f"OmniParser Replicate check: has_api_key={has_key}")
            return has_key
        else:
            return self._check_local_server()

    def _check_local_server(self) -> bool:
        """Check if local server is available."""
        import requests

        try:
            response = requests.get(f"{self.local_url}/health", timeout=2)
            return response.status_code == 200
        except Exception:
            return False


def create_omni_parser_client(
    backend: str = "replicate",
    api_key: Optional[str] = None,
    local_url: str = "http://localhost:8000",
    box_threshold: float = 0.05,
) -> Optional[OmniParserClient]:
    """Factory function to create OmniParser client with error handling.

    Args:
        backend: "replicate" or "local"
        api_key: API key for Replicate
        local_url: URL for local server
        box_threshold: Detection threshold

    Returns:
        OmniParserClient instance or None if not available
    """
    try:
        client = OmniParserClient(
            backend=backend,
            api_key=api_key,
            local_url=local_url,
            box_threshold=box_threshold,
        )
        if client.is_available():
            logger.info(f"OmniParser client initialized (backend: {backend})")
            return client
        else:
            logger.warning(f"OmniParser backend '{backend}' not available")
            return None
    except Exception as e:
        logger.warning(f"Failed to initialize OmniParser client: {e}")
        return None
