"""Max actions per Action Batch is a config value: default 5, 1 = single action."""

from mobile_crawler.domain.crawler_agent.config_manager.config_manager import AgentConfig, CrawlerConfig


def test_default_max_actions_per_batch_is_five():
    assert AgentConfig().max_actions_per_batch == 5


def test_max_actions_per_batch_is_loaded_from_config_dict():
    config = CrawlerConfig.from_dict({"agent": {"max_actions_per_batch": 3}})

    assert config.agent.max_actions_per_batch == 3


def test_max_actions_per_batch_defaults_when_absent_from_config_dict():
    config = CrawlerConfig.from_dict({"agent": {}})

    assert config.agent.max_actions_per_batch == 5
