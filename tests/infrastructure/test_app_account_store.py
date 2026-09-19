"""Tests for AppAccountStore."""

import pytest

from mobile_crawler.infrastructure.app_account_store import AppAccount, AppAccountStore
from mobile_crawler.infrastructure.user_config_store import UserConfigStore


@pytest.fixture
def config_store(tmp_path):
    store = UserConfigStore(tmp_path / "user_config.db")
    store.create_schema()
    yield store
    store.close()


def test_get_returns_none_when_no_account(config_store):
    assert AppAccountStore(config_store).get("com.a") is None


def test_save_and_get_round_trip(config_store):
    store = AppAccountStore(config_store)
    store.save("com.a", AppAccount("alice", "pw-a", "alice+a@gmail.com"))
    assert store.get("com.a") == AppAccount("alice", "pw-a", "alice+a@gmail.com")


def test_packages_are_isolated(config_store):
    store = AppAccountStore(config_store)
    store.save("com.a", AppAccount("alice", "pw-a"))
    store.save("com.b", AppAccount("bob", "pw-b"))
    assert store.get("com.a").username == "alice"
    assert store.get("com.b").username == "bob"
    assert store.get("com.c") is None


def test_password_not_in_plain_settings(config_store):
    AppAccountStore(config_store).save("com.a", AppAccount("alice", "s3cret-pw"))
    for value in config_store.get_all_settings().values():
        assert "s3cret-pw" not in str(value)


def test_save_overwrites_and_delete_removes(config_store):
    store = AppAccountStore(config_store)
    store.save("com.a", AppAccount("alice", "old"))
    store.save("com.a", AppAccount("alice2", "new"))
    assert store.get("com.a") == AppAccount("alice2", "new")
    store.delete("com.a")
    assert store.get("com.a") is None
    assert config_store.get_secret_plaintext("app_account_password::com.a") is None
