"""Resolves an installed package's display name and icon.

Tries Local Resolution first (pulling the APK from the device and parsing it
with androguard, since the package is confirmed installed there), then falls
back to Network Resolution (a Play Store lookup) when local parsing fails or
the app isn't published there. Results are cached on disk so repeat lookups
don't re-pull/re-parse or re-hit the network.

See CONTEXT.md for the App Metadata / Local Resolution / Network Resolution /
App Metadata Cache vocabulary.
"""

import datetime
import json
import logging
import re
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_NETWORK_CACHE_TTL = datetime.timedelta(days=30)
_RASTER_ICON_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")


@dataclass
class AppMetadata:
    """Resolved display metadata for a package."""

    package: str
    label: str
    icon_path: Path | None
    source: str  # "local", "network", or "unresolved"


class AppMetadataResolver:
    """Resolves and caches App Metadata (label + icon) for installed packages."""

    def __init__(self, cache_dir: Path | None = None):
        if cache_dir is None:
            from mobile_crawler.config.paths import get_app_data_dir

            cache_dir = get_app_data_dir() / "app_metadata_cache"

        self._cache_dir = cache_dir
        self._icons_dir = cache_dir / "icons"
        self._icons_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = cache_dir / "index.json"
        self._lock = threading.Lock()

    def resolve(self, device_id: str, package: str) -> AppMetadata:
        """Resolve display metadata for `package`, installed on `device_id`."""
        version_code = self._get_version_code(device_id, package)

        if version_code:
            cache_key = f"{package}:{version_code}"
            cached = self._cache_get(cache_key)
            if cached:
                return cached

        network_key = f"{package}:network"
        cached_network = self._cache_get(network_key)
        if cached_network:
            return cached_network

        local_result = self._resolve_local(device_id, package)
        if local_result and version_code:
            self._cache_put(f"{package}:{version_code}", local_result)
            return local_result

        network_result = self._resolve_network(package)
        if network_result:
            self._cache_put(network_key, network_result)
            return network_result

        unresolved = AppMetadata(package=package, label=package, icon_path=None, source="unresolved")
        self._cache_put(network_key, unresolved)
        return unresolved

    def _get_version_code(self, device_id: str, package: str) -> str | None:
        try:
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", "dumpsys", "package", package],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (subprocess.SubprocessError, OSError):
            return None

        match = re.search(r"versionCode=(\d+)", result.stdout)
        return match.group(1) if match else None

    def _resolve_local(self, device_id: str, package: str) -> AppMetadata | None:
        remote_apk_path = self._get_remote_apk_path(device_id, package)
        if not remote_apk_path:
            return None

        with tempfile.TemporaryDirectory(prefix="mobile_crawler_apk_") as tmp_dir:
            local_apk_path = Path(tmp_dir) / "app.apk"
            try:
                result = subprocess.run(
                    ["adb", "-s", device_id, "pull", remote_apk_path, str(local_apk_path)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode != 0 or not local_apk_path.exists():
                    return None

                return self._parse_apk(package, local_apk_path)
            except (subprocess.SubprocessError, OSError) as e:
                logger.debug(f"Local resolution failed for {package}: {e}")
                return None

    def _get_remote_apk_path(self, device_id: str, package: str) -> str | None:
        try:
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", "pm", "path", package],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (subprocess.SubprocessError, OSError):
            return None

        if result.returncode != 0:
            return None

        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("package:") and line.endswith("base.apk"):
                return line.replace("package:", "", 1)

        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("package:"):
                return line.replace("package:", "", 1)

        return None

    def _parse_apk(self, package: str, apk_path: Path) -> AppMetadata | None:
        try:
            from androguard.core.apk import APK
        except ImportError:
            logger.warning("androguard is not installed; skipping local app metadata resolution")
            return None

        try:
            apk = APK(str(apk_path))
            label = apk.get_app_name() or package
            icon_path = self._extract_icon(apk, package)
            return AppMetadata(package=package, label=label, icon_path=icon_path, source="local")
        except Exception as e:
            logger.debug(f"androguard failed to parse {package}: {e}")
            return None

    def _extract_icon(self, apk, package: str) -> Path | None:
        try:
            icon_resource_path = apk.get_app_icon()
        except Exception:
            return None

        if not icon_resource_path or not icon_resource_path.lower().endswith(_RASTER_ICON_SUFFIXES):
            # Adaptive/vector icons aren't trivially rasterizable; caller falls
            # back to a generic icon (best-effort, per design decision).
            return None

        try:
            icon_bytes = apk.get_file(icon_resource_path)
        except Exception:
            return None

        suffix = Path(icon_resource_path).suffix or ".png"
        icon_path = self._icons_dir / f"{self._safe_filename(package)}{suffix}"
        icon_path.write_bytes(icon_bytes)
        return icon_path

    def _resolve_network(self, package: str) -> AppMetadata | None:
        try:
            import google_play_scraper
        except ImportError:
            logger.warning("google-play-scraper is not installed; skipping network app metadata resolution")
            return None

        try:
            details = google_play_scraper.app(package)
        except Exception as e:
            logger.debug(f"Network resolution failed for {package}: {e}")
            return None

        label = details.get("title") or package
        icon_url = details.get("icon")
        icon_path = self._download_icon(icon_url, package) if icon_url else None
        return AppMetadata(package=package, label=label, icon_path=icon_path, source="network")

    def _download_icon(self, icon_url: str, package: str) -> Path | None:
        try:
            import requests

            response = requests.get(icon_url, timeout=15)
            response.raise_for_status()
        except Exception as e:
            logger.debug(f"Failed to download icon for {package}: {e}")
            return None

        icon_path = self._icons_dir / f"{self._safe_filename(package)}_network.png"
        icon_path.write_bytes(response.content)
        return icon_path

    def _safe_filename(self, package: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]", "_", package)

    def _cache_get(self, key: str) -> AppMetadata | None:
        with self._lock:
            index = self._load_index()

        entry = index.get(key)
        if not entry:
            return None

        if entry.get("source") in ("network", "unresolved"):
            resolved_at = datetime.datetime.fromisoformat(entry["resolved_at"])
            if datetime.datetime.now(datetime.UTC) - resolved_at > _NETWORK_CACHE_TTL:
                return None

        icon_path = Path(entry["icon_path"]) if entry.get("icon_path") else None
        if icon_path and not icon_path.exists():
            icon_path = None

        return AppMetadata(package=entry["package"], label=entry["label"], icon_path=icon_path, source=entry["source"])

    def _cache_put(self, key: str, metadata: AppMetadata) -> None:
        with self._lock:
            index = self._load_index()
            index[key] = {
                "package": metadata.package,
                "label": metadata.label,
                "icon_path": str(metadata.icon_path) if metadata.icon_path else None,
                "source": metadata.source,
                "resolved_at": datetime.datetime.now(datetime.UTC).isoformat(),
            }
            self._save_index(index)

    def _load_index(self) -> dict:
        if not self._index_path.exists():
            return {}
        try:
            return json.loads(self._index_path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_index(self, index: dict) -> None:
        self._index_path.write_text(json.dumps(index, indent=2))
