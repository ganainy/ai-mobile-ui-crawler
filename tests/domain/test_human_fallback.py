from mobile_crawler.domain.human_fallback import (
    FallbackStatus,
    HumanFallback,
    HumanFallbackConfig,
    HumanReply,
    RequestKind,
)
from mobile_crawler.infrastructure.user_config_store import UserConfigStore


def test_user_answers_with_code():
    seen = []

    def prompter(request, timeout):
        seen.append((request.kind, timeout))
        return HumanReply(code="123456")

    fb = HumanFallback(HumanFallbackConfig(enabled=True, timeout_minutes=2), prompter)
    out = fb.request(RequestKind.CODE, "Enter the SMS code")
    assert out.answered and out.code == "123456"
    assert seen == [(RequestKind.CODE, 120.0)]
    assert fb.skipped_reason is None


def test_manual_step_continue():
    fb = HumanFallback(HumanFallbackConfig(enabled=True), lambda r, t: HumanReply())
    out = fb.request(RequestKind.MANUAL_STEP, "Finish sign-in")
    assert out.answered and out.code is None


def test_timeout_skips_auth_and_records_note():
    fb = HumanFallback(HumanFallbackConfig(enabled=True, timeout_minutes=5), lambda r, t: None)
    out = fb.request(RequestKind.CODE, "code?")
    assert out.status is FallbackStatus.TIMED_OUT
    assert "5 min" in out.skip_note
    assert fb.skipped_reason == out.skip_note


def test_disabled_skips_immediately_without_prompting():
    def prompter(request, timeout):
        raise AssertionError("must not prompt")

    fb = HumanFallback(HumanFallbackConfig(enabled=False), prompter)
    out = fb.request(RequestKind.CODE, "code?")
    assert out.status is FallbackStatus.DISABLED
    assert "Human Fallback is off" in out.skip_note


def test_user_skips():
    fb = HumanFallback(HumanFallbackConfig(enabled=True), lambda r, t: HumanReply(skipped=True))
    out = fb.request(RequestKind.CODE, "code?")
    assert out.status is FallbackStatus.DECLINED and out.skip_note


def test_config_from_store_defaults_and_values(tmp_path):
    store = UserConfigStore(tmp_path / "c.db")
    store.create_schema()
    assert HumanFallbackConfig.from_store(store) == HumanFallbackConfig(False, 5)
    store.set_setting("human_fallback_enabled", True, "bool")
    store.set_setting("human_fallback_timeout_minutes", 12, "int")
    assert HumanFallbackConfig.from_store(store) == HumanFallbackConfig(True, 12)


def test_config_from_store_enabled_override_wins_over_persisted_value(tmp_path):
    store = UserConfigStore(tmp_path / "c.db")
    store.create_schema()
    store.set_setting("human_fallback_enabled", True, "bool")

    assert HumanFallbackConfig.from_store(store, enabled_override=False) == HumanFallbackConfig(False, 5)
    assert HumanFallbackConfig.from_store(store, enabled_override=True) == HumanFallbackConfig(True, 5)
    assert HumanFallbackConfig.from_store(store, enabled_override=None) == HumanFallbackConfig(True, 5)
