"""Tests for the scenarios CLI commands (Guided Scenarios list per package)."""

from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from mobile_crawler.cli.main import cli
from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.domain.guided_scenarios_generator import (
    GuidedScenariosResult,
    guided_scenarios_config_key,
    guided_scenarios_url_override_config_key,
)
from mobile_crawler.infrastructure.user_config_store import UserConfigStore

PKG = "com.example.app"


@pytest.fixture
def store(tmp_path):
    store = UserConfigStore(tmp_path / "user_config.db")
    store.create_schema()
    with patch(
        "mobile_crawler.cli.commands.scenarios.ConfigManager",
        side_effect=lambda: ConfigManager(store),
    ):
        yield store


def _scenarios(store):
    return store.get_setting(guided_scenarios_config_key(PKG), default=[])


def _invoke(*args):
    return CliRunner().invoke(cli, ["scenarios", *args])


def test_list_prints_numbered_scenarios_and_url_override(store):
    store.set_setting(guided_scenarios_config_key(PKG), ["Open search", "Open profile"], "json")
    store.set_setting(guided_scenarios_url_override_config_key(PKG), "https://example.com", "string")

    result = _invoke("list", "--package", PKG)

    assert result.exit_code == 0, result.output
    assert "1. Open search" in result.output
    assert "2. Open profile" in result.output
    assert "https://example.com" in result.output


def test_list_with_no_scenarios_says_so(store):
    result = _invoke("list", "--package", PKG)

    assert result.exit_code == 0, result.output
    assert f"No guided scenarios for {PKG}" in result.output


def test_list_is_scoped_to_the_package(store):
    store.set_setting(guided_scenarios_config_key("com.other"), ["Other app thing"], "json")

    result = _invoke("list", "--package", PKG)

    assert "Other app thing" not in result.output


def test_set_replaces_the_whole_list(store):
    store.set_setting(guided_scenarios_config_key(PKG), ["old"], "json")

    result = _invoke("set", "--package", PKG, "First", "  Second  ", "")

    assert result.exit_code == 0, result.output
    assert _scenarios(store) == ["First", "Second"]


def test_set_with_no_scenarios_clears_the_list(store):
    store.set_setting(guided_scenarios_config_key(PKG), ["old"], "json")

    result = _invoke("set", "--package", PKG)

    assert result.exit_code == 0, result.output
    assert _scenarios(store) == []


def test_set_website_url_only_keeps_the_list(store):
    store.set_setting(guided_scenarios_config_key(PKG), ["keep me"], "json")

    result = _invoke("set", "--package", PKG, "--website-url", "https://example.com")

    assert result.exit_code == 0, result.output
    assert _scenarios(store) == ["keep me"]
    assert store.get_setting(guided_scenarios_url_override_config_key(PKG)) == "https://example.com"


def test_set_empty_website_url_clears_the_override(store):
    store.set_setting(guided_scenarios_url_override_config_key(PKG), "https://example.com", "string")

    result = _invoke("set", "--package", PKG, "--website-url", "", "A")

    assert result.exit_code == 0, result.output
    assert not store.get_setting(guided_scenarios_url_override_config_key(PKG))
    assert _scenarios(store) == ["A"]


def test_add_appends_by_default(store):
    store.set_setting(guided_scenarios_config_key(PKG), ["A"], "json")

    result = _invoke("add", "--package", PKG, "B")

    assert result.exit_code == 0, result.output
    assert _scenarios(store) == ["A", "B"]


def test_add_at_position_inserts(store):
    store.set_setting(guided_scenarios_config_key(PKG), ["A", "C"], "json")

    result = _invoke("add", "--package", PKG, "--position", "2", "B")

    assert result.exit_code == 0, result.output
    assert _scenarios(store) == ["A", "B", "C"]


def test_add_rejects_blank_text(store):
    result = _invoke("add", "--package", PKG, "   ")

    assert result.exit_code != 0
    assert _scenarios(store) == []


def test_edit_replaces_one_entry(store):
    store.set_setting(guided_scenarios_config_key(PKG), ["A", "B"], "json")

    result = _invoke("edit", "--package", PKG, "2", "Bee")

    assert result.exit_code == 0, result.output
    assert _scenarios(store) == ["A", "Bee"]


def test_remove_deletes_one_entry(store):
    store.set_setting(guided_scenarios_config_key(PKG), ["A", "B", "C"], "json")

    result = _invoke("remove", "--package", PKG, "2")

    assert result.exit_code == 0, result.output
    assert _scenarios(store) == ["A", "C"]


def test_move_reorders_an_entry(store):
    store.set_setting(guided_scenarios_config_key(PKG), ["A", "B", "C"], "json")

    result = _invoke("move", "--package", PKG, "3", "1")

    assert result.exit_code == 0, result.output
    assert _scenarios(store) == ["C", "A", "B"]


@pytest.mark.parametrize(
    "args",
    [
        ("edit", "--package", PKG, "3", "x"),
        ("remove", "--package", PKG, "0"),
        ("move", "--package", PKG, "1", "3"),
        ("add", "--package", PKG, "--position", "4", "x"),
    ],
)
def test_out_of_range_index_fails_without_changing_the_list(store, args):
    store.set_setting(guided_scenarios_config_key(PKG), ["A", "B"], "json")

    result = _invoke(*args)

    assert result.exit_code != 0
    assert "out of range" in result.output
    assert _scenarios(store) == ["A", "B"]


def test_generate_replaces_list_and_saves_url_override(store):
    store.set_setting(guided_scenarios_config_key(PKG), ["old"], "json")
    generate = AsyncMock(return_value=GuidedScenariosResult(scenarios=["New 1", "New 2"]))

    with patch("mobile_crawler.domain.guided_scenarios_generator.generate_guided_scenarios", generate):
        result = _invoke("generate", "--package", PKG, "--website-url", "https://example.com")

    assert result.exit_code == 0, result.output
    assert generate.await_args.args[1:] == (PKG, "https://example.com")
    assert _scenarios(store) == ["New 1", "New 2"]
    assert store.get_setting(guided_scenarios_url_override_config_key(PKG)) == "https://example.com"
    assert "1. New 1" in result.output


def test_generate_without_url_uses_the_saved_override(store):
    store.set_setting(guided_scenarios_url_override_config_key(PKG), "https://saved.example", "string")
    generate = AsyncMock(return_value=GuidedScenariosResult(scenarios=["X"]))

    with patch("mobile_crawler.domain.guided_scenarios_generator.generate_guided_scenarios", generate):
        result = _invoke("generate", "--package", PKG)

    assert result.exit_code == 0, result.output
    assert generate.await_args.args[1:] == (PKG, "https://saved.example")


def test_generate_warning_keeps_the_old_list_and_fails(store):
    store.set_setting(guided_scenarios_config_key(PKG), ["old"], "json")
    generate = AsyncMock(return_value=GuidedScenariosResult(scenarios=[], warning="No web information found."))

    with patch("mobile_crawler.domain.guided_scenarios_generator.generate_guided_scenarios", generate):
        result = _invoke("generate", "--package", PKG, "--website-url", "https://example.com")

    assert result.exit_code != 0
    assert "No web information found." in result.output
    assert _scenarios(store) == ["old"]
    assert not store.get_setting(guided_scenarios_url_override_config_key(PKG))


def test_scenarios_group_is_registered():
    result = CliRunner().invoke(cli, ["scenarios", "--help"])

    assert result.exit_code == 0
    for name in ("generate", "list", "set", "add", "edit", "remove", "move"):
        assert name in result.output


def test_generate_passes_single_run_llm_overrides_without_saving_them(store):
    store.set_setting("ai_provider", "gemini", "string")
    generate = AsyncMock(return_value=GuidedScenariosResult(scenarios=["X"]))

    with patch("mobile_crawler.domain.guided_scenarios_generator.generate_guided_scenarios", generate):
        result = _invoke(
            "generate", "--package", PKG,
            "--provider", "openai", "--model", "gpt-x", "--exploration-objective", "payments",
        )

    assert result.exit_code == 0, result.output
    config_manager = generate.await_args.args[0]
    assert config_manager.get("ai_provider") == "openai"
    assert config_manager.get("ai_model") == "gpt-x"
    assert config_manager.get("exploration_objective") == "payments"
    assert store.get_setting("ai_provider") == "gemini"
    assert store.get_setting("ai_model") is None


def test_generate_error_is_reported_without_a_traceback(store):
    store.set_setting(guided_scenarios_config_key(PKG), ["old"], "json")
    generate = AsyncMock(side_effect=RuntimeError("network down"))

    with patch("mobile_crawler.domain.guided_scenarios_generator.generate_guided_scenarios", generate):
        result = _invoke("generate", "--package", PKG)

    assert result.exit_code == 1
    assert "Failed to generate scenarios: network down" in result.output
    assert _scenarios(store) == ["old"]
