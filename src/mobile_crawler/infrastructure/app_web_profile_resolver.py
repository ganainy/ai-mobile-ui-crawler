"""Resolves an App Web Profile: descriptive text about what a target app does.

Used to generate Guided Scenarios (see CONTEXT.md for both terms). Deliberately
kept separate from AppMetadataResolver, which resolves display label/icon, not
descriptive content — see
docs/adr/0003-resolve-app-web-profile-separately-and-defer-scrapling.md for why.
"""

import datetime
import html.parser
import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_CACHE_TTL = datetime.timedelta(days=30)
_PLAY_STORE_TIMEOUT_SECONDS = 15
_WEBSITE_TIMEOUT_SECONDS = 10
_MAX_WEBSITE_CHARS = 8000
_MIN_USEFUL_WEBSITE_CHARS = 200


@dataclass
class AppWebProfile:
    """Resolved App Web Profile text for a package."""

    package: str
    play_store_description: str
    website_url: str | None
    website_text: str
    source: str  # "network", "website_only", or "unresolved"


class _VisibleTextExtractor(html.parser.HTMLParser):
    """Extracts visible text from HTML, skipping script/style content."""

    _SKIP_TAGS = {"script", "style", "noscript", "template"}

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self.chunks.append(text)

    def get_text(self) -> str:
        return " ".join(self.chunks)


class AppWebProfileResolver:
    """Resolves and caches App Web Profile text (Play Store description + optional website text)."""

    def __init__(self, cache_dir: Path | None = None):
        if cache_dir is None:
            from mobile_crawler.config.paths import get_app_data_dir

            cache_dir = get_app_data_dir() / "app_web_profile_cache"

        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = cache_dir / "index.json"
        self._lock = threading.Lock()

    def resolve(self, package: str, website_url_override: str | None = None) -> AppWebProfile:
        """Resolve an App Web Profile for `package`.

        `website_url_override`, if given, is scraped instead of the Play
        Store listing's own developer website, and changing it busts the
        website-text cache entry (it's keyed by URL). It also skips the Play
        Store lookup entirely: that call is an unofficial scrape with no
        timeout of its own (see `_PLAY_STORE_TIMEOUT_SECONDS`) and is the
        least reliable step here, so an explicit override — which already
        tells us exactly what to scrape — bypasses it rather than waiting
        out a lookup whose only other output (`developerWebsite`) is moot.
        """
        if website_url_override:
            description, listed_website_url = "", None
        else:
            description, listed_website_url = self._resolve_play_store(package)
        website_url = website_url_override or listed_website_url

        website_text = ""
        if website_url:
            website_text = self._resolve_website(package, website_url)

        if description:
            source = "network"
        elif website_text:
            source = "website_only"
        else:
            source = "unresolved"

        return AppWebProfile(
            package=package,
            play_store_description=description,
            website_url=website_url,
            website_text=website_text,
            source=source,
        )

    def _resolve_play_store(self, package: str) -> tuple[str, str | None]:
        cache_key = f"{package}:playstore"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached.get("description", ""), cached.get("website_url")

        try:
            import google_play_scraper
        except ImportError:
            logger.warning("google-play-scraper is not installed; skipping Play Store Web Profile Resolution")
            return "", None

        # google_play_scraper.app() calls urllib.request.urlopen() with no timeout of its
        # own, so a stalled connection can block forever. Run it on a daemon thread and
        # bound the wait ourselves; an orphaned call is left to die with the thread instead
        # of hanging the caller (or, if it happened on the main thread, the whole app).
        result: dict = {}

        def _fetch() -> None:
            try:
                result["details"] = google_play_scraper.app(package)
            except Exception as e:
                result["error"] = e

        fetch_thread = threading.Thread(target=_fetch, daemon=True)
        fetch_thread.start()
        fetch_thread.join(timeout=_PLAY_STORE_TIMEOUT_SECONDS)

        if fetch_thread.is_alive():
            logger.warning(
                f"Web Profile Resolution: Play Store lookup timed out for {package} "
                f"after {_PLAY_STORE_TIMEOUT_SECONDS}s"
            )
            return "", None
        if "error" in result:
            logger.info(f"Web Profile Resolution: Play Store lookup failed for {package}: {result['error']}")
            return "", None

        details = result["details"]

        description = (details.get("description") or "").strip()
        website_url = (details.get("developerWebsite") or "").strip() or None

        self._cache_put(cache_key, {"description": description, "website_url": website_url})
        return description, website_url

    def _resolve_website(self, package: str, url: str) -> str:
        cache_key = f"{package}:site:{url}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached.get("text", "")

        text = self._fetch_website_text(url)
        self._cache_put(cache_key, {"text": text})
        return text

    def _fetch_website_text(self, url: str) -> str:
        try:
            response = requests.get(
                url,
                timeout=_WEBSITE_TIMEOUT_SECONDS,
                headers={"User-Agent": "Mozilla/5.0 (compatible; mobile-crawler/1.0)"},
            )
            response.raise_for_status()
        except Exception as e:
            # Logged (not raised) so resolution falls back to the Play Store
            # description alone. If this shows up often for JS-heavy sites,
            # that's the signal to revisit scrapling (see ADR 0003).
            logger.warning(f"Web Profile Resolution: website fetch failed for {url}: {e}")
            return ""

        parser = _VisibleTextExtractor()
        try:
            parser.feed(response.text)
        except Exception as e:
            logger.warning(f"Web Profile Resolution: failed to parse HTML from {url}: {e}")
            return ""

        text = parser.get_text()[:_MAX_WEBSITE_CHARS]
        if len(text) < _MIN_USEFUL_WEBSITE_CHARS:
            logger.info(
                f"Web Profile Resolution: website {url} returned little usable text "
                f"({len(text)} chars) — likely JS-rendered; a plain-requests fetch may be "
                "insufficient for this site (see ADR 0003)."
            )
        return text

    def _cache_get(self, key: str) -> dict | None:
        with self._lock:
            index = self._load_index()

        entry = index.get(key)
        if not entry:
            return None

        resolved_at = datetime.datetime.fromisoformat(entry["resolved_at"])
        if datetime.datetime.now(datetime.UTC) - resolved_at > _CACHE_TTL:
            return None

        return entry["data"]

    def _cache_put(self, key: str, data: dict) -> None:
        with self._lock:
            index = self._load_index()
            index[key] = {
                "data": data,
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
