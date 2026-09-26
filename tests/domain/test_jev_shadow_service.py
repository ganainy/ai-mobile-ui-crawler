"""CrawlerAgentService attaches a Jev shadow to the Executor only when the setting is on and usable."""

import asyncio
from types import SimpleNamespace

import pytest

from mobile_crawler.domain.crawler_agent_service import CrawlerAgentService


class Config:
    def __init__(self, **values):
        self.values = values
        self.user_config_store = SimpleNamespace(get_secret_plaintext=lambda key: (_ for _ in ()).throw(KeyError(key)))

    def get(self, key, default=None):
        return self.values.get(key, default)


def make_service(tmp_path, **settings):
    service = CrawlerAgentService(Config(**settings), None, "dev-1")
    service.jev_shadow_path = str(tmp_path / "jev_shadow.jsonl")
    service._crawler_agent = SimpleNamespace(executor_agent=SimpleNamespace(shadow=None))
    return service


def attach(service):
    asyncio.run(service._attach_jev_shadow())
    return service._crawler_agent.executor_agent.shadow


@pytest.fixture(autouse=True)
def no_env_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)


def test_off_by_default_no_shadow_is_attached(tmp_path):
    assert attach(make_service(tmp_path, openrouter_api_key="k")) is None


def test_enabled_attaches_shadow_with_model_and_path(tmp_path):
    service = make_service(
        tmp_path, jev_shadow_enabled=True, openrouter_api_key="k", jev_shadow_model="~typesafe/jev-x"
    )

    shadow = attach(service)

    assert shadow.model == "~typesafe/jev-x"
    assert shadow.jsonl_path == tmp_path / "jev_shadow.jsonl"
    assert shadow.api_key == "k"


def test_enabled_without_key_attaches_nothing(tmp_path):
    assert attach(make_service(tmp_path, jev_shadow_enabled=True)) is None


def test_non_reasoning_agent_without_executor_is_left_alone(tmp_path):
    service = make_service(tmp_path, jev_shadow_enabled=True, openrouter_api_key="k")
    service._crawler_agent = SimpleNamespace(executor_agent=None)

    asyncio.run(service._attach_jev_shadow())

    assert service._jev_shadow is None
