"""Generates a Guided Scenarios list for an app from its App Web Profile.

See CONTEXT.md for the Guided Scenarios / App Web Profile / Web Profile
Resolution vocabulary, and docs/adr/0003-resolve-app-web-profile-separately-
and-defer-scrapling.md for why this doesn't reuse AppMetadataResolver or
CrawlerAgentService's LLM setup directly.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass

from llama_index.core.base.llms.types import ChatMessage

from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.domain.crawler_agent.agent.utils.inference import acall_with_retries
from mobile_crawler.domain.crawler_agent.agent.utils.llm_picker import load_llm
from mobile_crawler.infrastructure.app_web_profile_resolver import AppWebProfileResolver

logger = logging.getLogger("crawler_agent")

_MAX_SCENARIOS = 12
_MAX_PROFILE_CHARS = 6000
# acall_with_retries defaults to a 500s-per-attempt timeout, sized for long crawl-agent
# steps. This is a one-off UI-triggered text call, so it gets its own much shorter budget.
_LLM_TIMEOUT_SECONDS = 45
_LLM_RETRIES = 2

# Mirrors the provider mapping in CrawlerAgentService._get_crawler_agent_config,
# duplicated (not imported) because that method builds a full crawler-agent
# config (device, omniparser, tracing...) this one-off text call doesn't need.
_PROVIDER_MAPPING = {
    "gemini": "GoogleGenAI",
    "openai": "OpenAI",
    "anthropic": "AnthropicAI",
    "ollama": "Ollama",
    "openrouter": "OpenRouter",
}

_PROVIDER_API_KEY_ENV = {
    "gemini": ("gemini_api_key", ["GEMINI_API_KEY", "GOOGLE_API_KEY"]),
    "openrouter": ("openrouter_api_key", ["OPENROUTER_API_KEY"]),
    "openai": ("openai_api_key", ["OPENAI_API_KEY"]),
    "anthropic": ("anthropic_api_key", ["ANTHROPIC_API_KEY"]),
}

_EXTRACTION_PROMPT = """You are helping configure an autonomous Android UI crawler for the app "{package}".

Below is publicly available text describing what this app does. Based on it, produce an ordered checklist \
of specific pages, screens, or user flows the crawler should try to visit (e.g. "Open the search screen and \
run a search", "Open the user profile / account settings screen", "Add an item to the cart or wishlist").

Only include scenarios you can reasonably infer are real features of this app from the text below. If the \
text gives no useful information, return an empty list. Do not invent features the text doesn't support.
{objective_section}
Respond with ONLY a JSON array of strings, no other text, no markdown code fence. At most {max_scenarios} items.

<app_web_profile>
{profile_text}
</app_web_profile>"""

_OBJECTIVE_SECTION_TEMPLATE = """
The person running this crawl is especially interested in: "{exploration_objective}". Where the app_web_profile \
text supports it, prioritize and order scenarios toward that interest — but still only include scenarios \
grounded in that text; do not invent features just to match this interest.
"""


def guided_scenarios_config_key(app_package: str) -> str:
    """Config key under which an app's persisted Guided Scenarios list is stored."""
    return f"guided_scenarios::{app_package}"


def guided_scenarios_url_override_config_key(app_package: str) -> str:
    """Config key under which an app's persisted website-URL override is stored."""
    return f"guided_scenarios_url_override::{app_package}"


@dataclass
class GuidedScenariosResult:
    """Result of a Guided Scenarios generation attempt.

    `warning` is set (and `scenarios` left empty) on any failure — per the
    fallback pattern used elsewhere (e.g. CompositeAppCardProvider): never
    silently produce garbage entries.
    """

    scenarios: list[str]
    warning: str | None = None


def _resolve_api_key(config_manager: ConfigManager, primary_key: str, env_keys: list[str]) -> str | None:
    key_value = config_manager.get(primary_key)
    if not key_value:
        try:
            key_value = config_manager.user_config_store.get_secret_plaintext(primary_key)
        except (KeyError, AttributeError):
            key_value = None
    if not key_value:
        for env_key in env_keys:
            key_value = os.environ.get(env_key)
            if key_value:
                break
    return key_value


def _build_extraction_llm(config_manager: ConfigManager):
    ai_provider = config_manager.get("ai_provider", "gemini")
    ai_model = config_manager.get("ai_model", "gemini-1.5-flash")

    if ai_provider not in _PROVIDER_MAPPING:
        raise ValueError(f"Unsupported AI provider: {ai_provider}")

    api_key = None
    if ai_provider in _PROVIDER_API_KEY_ENV:
        primary_key, env_keys = _PROVIDER_API_KEY_ENV[ai_provider]
        api_key = _resolve_api_key(config_manager, primary_key, env_keys)

    return load_llm(
        provider_name=_PROVIDER_MAPPING[ai_provider],
        model=ai_model,
        temperature=0.0,
        max_tokens=1024,
        api_key=api_key,
    )


def _parse_scenarios(raw_text: str) -> list[str] | None:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]

    try:
        parsed = json.loads(text.strip())
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, list):
        return None

    scenarios = [str(item).strip() for item in parsed if str(item).strip()]
    return scenarios[:_MAX_SCENARIOS]


async def generate_guided_scenarios(
    config_manager: ConfigManager,
    app_package: str,
    website_url_override: str | None = None,
) -> GuidedScenariosResult:
    """Resolve an App Web Profile for `app_package` and extract a Guided Scenarios list from it.

    If an `exploration_objective` is already set on `config_manager` (the same
    free-text field used at crawl-start), the extraction is tailored toward
    it — scenarios are still only ever drawn from the resolved App Web
    Profile text, never invented to match the objective.

    Never raises — failures are reported via `GuidedScenariosResult.warning`
    with an empty scenario list, per the fallback pattern used elsewhere in
    this codebase (e.g. CompositeAppCardProvider).
    """
    resolver = AppWebProfileResolver()
    profile = await asyncio.to_thread(resolver.resolve, app_package, website_url_override or None)

    profile_text = "\n\n".join(
        part for part in (profile.play_store_description, profile.website_text) if part
    ).strip()

    if not profile_text:
        return GuidedScenariosResult(
            scenarios=[],
            warning=(
                "No web information could be found for this app (no Play Store listing or "
                "reachable website). Add scenarios manually."
            ),
        )

    try:
        llm = _build_extraction_llm(config_manager)
        exploration_objective = (config_manager.get("exploration_objective") or "").strip()
        objective_section = (
            _OBJECTIVE_SECTION_TEMPLATE.format(exploration_objective=exploration_objective)
            if exploration_objective
            else ""
        )
        prompt = _EXTRACTION_PROMPT.format(
            package=app_package,
            profile_text=profile_text[:_MAX_PROFILE_CHARS],
            max_scenarios=_MAX_SCENARIOS,
            objective_section=objective_section,
        )
        response = await acall_with_retries(
            llm,
            [ChatMessage(role="user", content=prompt)],
            retries=_LLM_RETRIES,
            timeout=_LLM_TIMEOUT_SECONDS,
        )
        raw_content = response.message.content or ""
        scenarios = _parse_scenarios(raw_content)
    except Exception as e:
        logger.warning(f"Guided Scenarios generation failed for {app_package}: {e}")
        return GuidedScenariosResult(
            scenarios=[],
            warning="Failed to generate scenarios from app info. Try again or add them manually.",
        )

    if scenarios is None:
        logger.warning(
            f"Guided Scenarios generation returned malformed output for {app_package}: {raw_content!r}"
        )
        return GuidedScenariosResult(
            scenarios=[],
            warning="AI returned an unexpected response while generating scenarios. Try again or add them manually.",
        )

    if not scenarios:
        return GuidedScenariosResult(
            scenarios=[],
            warning="No specific scenarios could be inferred from this app's web info. Add scenarios manually.",
        )

    return GuidedScenariosResult(scenarios=scenarios)
