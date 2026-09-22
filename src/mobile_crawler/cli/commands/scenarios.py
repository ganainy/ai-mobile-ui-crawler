"""CLI commands for an app's Guided Scenarios list (the GUI's Guided Scenarios settings group).

Reads and writes the same `guided_scenarios::<pkg>` and
`guided_scenarios_url_override::<pkg>` settings as the GUI. Indexes are 1-based,
matching what `scenarios list` prints.
"""

import asyncio

import click

from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.domain import guided_scenarios_generator
from mobile_crawler.domain.guided_scenarios_generator import (
    guided_scenarios_config_key,
    guided_scenarios_url_override_config_key,
)

package_option = click.option("--package", "-p", required=True, help="App package name")


def _config_manager() -> ConfigManager:
    config_manager = ConfigManager()
    config_manager.user_config_store.create_schema()
    return config_manager


def _load(config_manager: ConfigManager, package: str) -> list[str]:
    scenarios = config_manager.user_config_store.get_setting(guided_scenarios_config_key(package), default=[])
    return list(scenarios) if isinstance(scenarios, list) else []


def _save(config_manager: ConfigManager, package: str, scenarios: list[str]) -> None:
    config_manager.user_config_store.set_setting(guided_scenarios_config_key(package), scenarios, "json")


def _load_url_override(config_manager: ConfigManager, package: str) -> str:
    return config_manager.user_config_store.get_setting(
        guided_scenarios_url_override_config_key(package), default=""
    ) or ""


def _save_url_override(config_manager: ConfigManager, package: str, url: str) -> None:
    config_manager.user_config_store.set_setting(guided_scenarios_url_override_config_key(package), url, "string")


def _clean(texts) -> list[str]:
    """Strip each entry and drop blank ones, like the GUI list editor does on save."""
    return [text.strip() for text in texts if text.strip()]


def _require_text(text: str) -> str:
    text = text.strip()
    if not text:
        raise click.BadParameter("scenario text must not be blank", param_hint="TEXT")
    return text


def _require_index(index: int, count: int, name: str = "INDEX") -> int:
    """Turn a 1-based `index` into a 0-based one, failing if it isn't within 1..count."""
    if not 1 <= index <= count:
        raise click.BadParameter(f"{index} is out of range (1-{count})", param_hint=name)
    return index - 1


def _echo_scenarios(package: str, scenarios: list[str]) -> None:
    if not scenarios:
        click.echo(f"No guided scenarios for {package}.")
        return
    for number, scenario in enumerate(scenarios, start=1):
        click.echo(f"{number}. {scenario}")


@click.group()
def scenarios():
    """Manage an app's Guided Scenarios (the pages/flows a crawl tries to visit)."""
    pass


@scenarios.command(name="list")
@package_option
def list_scenarios(package: str):
    """Print the Guided Scenarios for a package, numbered."""
    config_manager = _config_manager()
    url_override = _load_url_override(config_manager, package)
    if url_override:
        click.echo(f"Website URL override: {url_override}")
    _echo_scenarios(package, _load(config_manager, package))


@scenarios.command(name="set")
@package_option
@click.option(
    "--website-url",
    default=None,
    help="Website URL override used by `generate` (empty string clears it). Leaves the list alone if no TEXT is given.",
)
@click.argument("texts", metavar="[TEXT]...", nargs=-1)
def set_scenarios(package: str, website_url: str | None, texts: tuple[str, ...]):
    """Replace the whole Guided Scenarios list with TEXT... (no TEXT clears it)."""
    config_manager = _config_manager()
    if website_url is not None:
        _save_url_override(config_manager, package, website_url.strip())
        if not texts:
            click.echo(f"Website URL override for {package}: {website_url.strip() or '(none)'}")
            return
    scenarios_list = _clean(texts)
    _save(config_manager, package, scenarios_list)
    _echo_scenarios(package, scenarios_list)


@scenarios.command(name="add")
@package_option
@click.option("--position", type=int, default=None, help="1-based position to insert at (default: end)")
@click.argument("text")
def add_scenario(package: str, position: int | None, text: str):
    """Add one scenario, at the end or at --position."""
    text = _require_text(text)
    config_manager = _config_manager()
    scenarios_list = _load(config_manager, package)
    if position is None:
        scenarios_list.append(text)
    else:
        scenarios_list.insert(_require_index(position, len(scenarios_list) + 1, "--position"), text)
    _save(config_manager, package, scenarios_list)
    _echo_scenarios(package, scenarios_list)


@scenarios.command(name="edit")
@package_option
@click.argument("index", type=int)
@click.argument("text")
def edit_scenario(package: str, index: int, text: str):
    """Replace the text of scenario INDEX."""
    text = _require_text(text)
    config_manager = _config_manager()
    scenarios_list = _load(config_manager, package)
    scenarios_list[_require_index(index, len(scenarios_list))] = text
    _save(config_manager, package, scenarios_list)
    _echo_scenarios(package, scenarios_list)


@scenarios.command(name="remove")
@package_option
@click.argument("index", type=int)
def remove_scenario(package: str, index: int):
    """Remove scenario INDEX."""
    config_manager = _config_manager()
    scenarios_list = _load(config_manager, package)
    del scenarios_list[_require_index(index, len(scenarios_list))]
    _save(config_manager, package, scenarios_list)
    _echo_scenarios(package, scenarios_list)


@scenarios.command(name="move")
@package_option
@click.argument("index", type=int)
@click.argument("new_index", type=int)
def move_scenario(package: str, index: int, new_index: int):
    """Move scenario INDEX to position NEW_INDEX."""
    config_manager = _config_manager()
    scenarios_list = _load(config_manager, package)
    source = _require_index(index, len(scenarios_list))
    target = _require_index(new_index, len(scenarios_list), "NEW_INDEX")
    scenarios_list.insert(target, scenarios_list.pop(source))
    _save(config_manager, package, scenarios_list)
    _echo_scenarios(package, scenarios_list)


@scenarios.command(name="generate")
@package_option
@click.option(
    "--website-url",
    default=None,
    help="Website to read app info from, instead of the one found via the Play Store (default: the saved override).",
)
@click.option("--provider", help="AI provider for this generation only (default: the configured provider)")
@click.option("--model", help="AI model for this generation only (default: the configured model)")
@click.option(
    "--exploration-objective",
    help="Exploration Objective to tailor the scenarios to, for this generation only (default: the configured objective)",
)
def generate_scenarios(
    package: str,
    website_url: str | None,
    provider: str | None,
    model: str | None,
    exploration_objective: str | None,
):
    """Generate the Guided Scenarios list from the app's App Web Profile (Play Store listing / website).

    Replaces the current list on success; keeps it and exits non-zero otherwise.
    """
    config_manager = _config_manager()
    # Single-run overrides, like the matching `crawl` flags: never written to the store.
    for key, value in (("ai_provider", provider), ("ai_model", model), ("exploration_objective", exploration_objective)):
        if value is not None:
            config_manager.override(key, value)
    if website_url is None:
        website_url = _load_url_override(config_manager, package)
    website_url = website_url.strip()

    click.echo(f"Generating guided scenarios for {package}...", err=True)
    try:
        result = asyncio.run(
            guided_scenarios_generator.generate_guided_scenarios(config_manager, package, website_url or None)
        )
    except Exception as e:
        # generate_guided_scenarios only guards the LLM step; e.g. web profile resolution can still raise.
        click.echo(f"Failed to generate scenarios: {e}", err=True)
        raise SystemExit(1) from e

    if not result.scenarios:
        click.echo(result.warning or "No scenarios were generated.", err=True)
        raise SystemExit(1)

    # Same as the GUI: a successful Generate replaces the list and saves it with the URL override.
    _save(config_manager, package, result.scenarios)
    _save_url_override(config_manager, package, website_url)
    if result.warning:
        click.echo(result.warning, err=True)
    _echo_scenarios(package, result.scenarios)
