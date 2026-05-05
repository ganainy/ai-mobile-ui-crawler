"""OmniParser client for vision-based UI parsing."""

import base64
import io
import logging
import os
from enum import Enum
from typing import List, Dict, Any, Optional

import requests

logger = logging.getLogger(__name__)


class OmniParserBackend(Enum):
    REPLICATE = "replicate"
    LOCAL = "local"


class OmniParserClient:
    """Client for OmniParser vision-based UI parsing."""

    def __init__(self, config_manager, replicate_api_key: Optional[str] = None):
        self.config_manager = config_manager
        self._replicate_api_key = replicate_api_key
        self._backend = self._detect_backend()

    def _detect_backend(self) -> OmniParserBackend:
        preferred = self.config_manager.get("omniparser_backend", "replicate")
        if preferred == "local" and self.check_local_available():
            return OmniParserBackend.LOCAL
        return OmniParserBackend.REPLICATE

    @property
    def backend(self) -> OmniParserBackend:
        return self._backend

    def set_backend(self, backend: str) -> None:
        if backend == "local" and not self.check_local_available():
            logger.warning("Local backend not available, using Replicate")
            self._backend = OmniParserBackend.REPLICATE
        else:
            self._backend = OmniParserBackend.LOCAL if backend == "local" else OmniParserBackend.REPLICATE

    def check_local_available(self) -> bool:
        local_url = self.config_manager.get("omniparser_local_url", "http://localhost:8000")
        try:
            response = requests.get(f"{local_url}/health", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def parse(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        if self._backend == OmniParserBackend.LOCAL:
            return self._parse_local(image_bytes)
        else:
            return self._parse_replicate(image_bytes)

    def _parse_replicate(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        try:
            import replicate
        except ImportError:
            raise ImportError("replicate package required: pip install replicate")

        api_key = self._get_api_key()
        if not api_key:
            raise ValueError("Replicate API key not configured")

        replicate.api_token = api_key
        box_threshold = self.config_manager.get("omniparser_box_threshold", 0.05)

        try:
            output = replicate.run(
                "microsoft/omniparser-v2",
                input={"image": io.BytesIO(image_bytes), "box_threshold": box_threshold}
            )

            if isinstance(output, dict):
                return output.get("elements", output.get("parsed_content", []))
            elif isinstance(output, list):
                return output
            else:
                logger.warning(f"Unexpected Replicate output type: {type(output)}")
                return []

        except Exception as e:
            logger.error(f"Replicate API error: {e}")
            raise RuntimeError(f"OmniParser Replicate error: {e}")

    def _parse_local(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        local_url = self.config_manager.get("omniparser_local_url", "http://localhost:8000")
        box_threshold = self.config_manager.get("omniparser_box_threshold", 0.05)
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        try:
            response = requests.post(
                f"{local_url}/parse",
                json={"base64_image": b64_image, "box_threshold": box_threshold},
                timeout=30,
            )
            if response.status_code != 200:
                raise RuntimeError(f"Local OmniParser error: {response.status_code}")
            return response.json().get("elements", [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Local OmniParser connection error: {e}")
            raise

    def _get_api_key(self) -> Optional[str]:
        if self._replicate_api_key:
            return self._replicate_api_key
        try:
            from mobile_crawler.infrastructure.user_config_store import UserConfigStore
            store = UserConfigStore()
            key = store.get_secret_plaintext("omniparser_replicate_api_key")
            if key:
                return key
        except Exception:
            pass
        key = os.environ.get("REPLICATE_API_KEY")
        if key:
            return key
        return None
