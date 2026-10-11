from mobile_crawler.cli.omniparser_warmup_step import warm_up_omniparser_if_needed


class Cfg(dict):
    def get(self, key, default=None):
        return super().get(key, default)


def cfg(**kw):
    return Cfg(ui_parser_mode="boost", omniparser_backend="replicate", **kw)


def test_skipped_for_accessibility_mode(monkeypatch):
    called = []
    assert warm_up_omniparser_if_needed(Cfg(ui_parser_mode="accessibility"), lambda **k: called.append(k)) is None
    assert not called


def test_skipped_for_local_backend():
    assert warm_up_omniparser_if_needed(Cfg(ui_parser_mode="boost", omniparser_backend="local"), lambda **k: 1 / 0) is None


def test_skipped_when_keepalive_setting_is_off():
    assert warm_up_omniparser_if_needed(cfg(omniparser_keepalive_enabled=False), lambda **k: 1 / 0) is None


def test_no_key_is_reported(monkeypatch):
    monkeypatch.delenv("REPLICATE_API_KEY", raising=False)
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.setattr("mobile_crawler.config.api_keys.resolve_api_key", lambda *a, **k: None)
    assert "no Replicate API key" in warm_up_omniparser_if_needed(cfg(), lambda **k: 1 / 0)


def test_warmup_runs_and_never_raises(monkeypatch):
    monkeypatch.setattr("mobile_crawler.config.api_keys.resolve_api_key", lambda *a, **k: "key")
    seen = {}
    msg = warm_up_omniparser_if_needed(cfg(), lambda **k: seen.update(k))
    assert msg.startswith("OmniParser warm-up ok") and seen["api_key"] == "key"

    def boom(**k):
        raise RuntimeError("replicate down")

    assert "failed (replicate down)" in warm_up_omniparser_if_needed(cfg(), boom)
