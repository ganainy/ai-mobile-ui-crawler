"""Config snapshot captured at run start so runs can be compared later."""

import json

from mobile_crawler.domain.run_config_snapshot import build_config_snapshot, write_config_snapshot


class FakeConfig:
    def __init__(self, values):
        self.values = values

    def get(self, key, default=None):
        return self.values.get(key, default)


def test_snapshot_records_run_settings_and_guided_scenarios():
    config = FakeConfig(
        {
            "ai_provider": "gemini",
            "ai_model": "gemini-x",
            "limit_type": "steps",
            "max_steps": 40,
            "max_duration_seconds": 300,
            "top_bar_height": 80,
            "bottom_bar_height": 0,
            "guided_scenarios::com.x": ["Open settings"],
            "restart_app_before_run": False,
        }
    )

    snapshot = build_config_snapshot(config, "com.x", git_commit="abc1234")

    assert snapshot["ai_provider"] == "gemini"
    assert snapshot["ai_model"] == "gemini-x"
    assert snapshot["limit_type"] == "steps"
    assert snapshot["max_steps"] == 40
    assert snapshot["status_bar_exclusion_px"] == 80
    assert snapshot["bottom_bar_exclusion_px"] == 0
    assert snapshot["guided_scenarios"] == ["Open settings"]
    assert snapshot["git_commit"] == "abc1234"
    assert snapshot["restart_app_before_run"] is False


def test_snapshot_never_includes_secrets():
    config = FakeConfig(
        {
            "gemini_api_key": "SECRET-KEY",
            "langfuse_secret_key": "SECRET-LF",
            "replicate_api_key": "SECRET-R",
            "ai_model": "m",
        }
    )

    assert "SECRET" not in json.dumps(build_config_snapshot(config, "com.x", git_commit=None))


def test_snapshot_falls_back_to_legacy_step_limit_key():
    config = FakeConfig({"max_crawl_steps": 15, "max_crawl_duration_seconds": 600})

    snapshot = build_config_snapshot(config, "com.x", git_commit=None)

    assert snapshot["max_steps"] == 15
    assert snapshot["max_duration_seconds"] == 600


def test_write_config_snapshot_puts_json_in_session_data_folder(tmp_path):
    path = write_config_snapshot(str(tmp_path), {"ai_model": "m"})

    assert path == tmp_path / "data" / "config_snapshot.json"
    assert json.loads(path.read_text(encoding="utf-8")) == {"ai_model": "m"}
