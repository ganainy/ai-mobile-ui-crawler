"""Tests for action verifier."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from mobile_crawler.domain.action_verifier import (
    NAVIGATION_ACTIONS,
    ActionVerifier,
)


def _make_ui_state(text: str, elements=None):
    state = MagicMock()
    state.formatted_text = text
    state.elements = elements or []
    return state


@pytest.fixture
def mock_state_provider():
    return AsyncMock()


@pytest.fixture
def mock_driver():
    return AsyncMock()


@pytest.fixture
def verifier(mock_state_provider, mock_driver):
    return ActionVerifier(
        state_provider=mock_state_provider,
        driver=mock_driver,
    )


class TestNavigationActions:
    def test_navigation_actions_set(self):
        expected = {"back", "home", "click", "tap", "start_app", "launch_app", "recent_apps"}
        assert NAVIGATION_ACTIONS == expected


class TestActionVerifier:
    @pytest.mark.asyncio
    async def test_capture_pre_state_keys(self, verifier, mock_state_provider, mock_driver):
        mock_state_provider.get_state.return_value = _make_ui_state("hello", [1, 2, 3])
        mock_driver._get_current_app.return_value = "com.example.app"

        state = await verifier.capture_pre_state()
        assert "package" in state
        assert "ui_text_hash" in state
        assert "element_count" in state
        assert state["package"] == "com.example.app"
        assert state["element_count"] == 3

    @pytest.mark.asyncio
    async def test_verify_navigation_changed(self, verifier, mock_state_provider, mock_driver):
        """Navigation action with UI change verifies True."""
        pre_state = {"package": "com.example.app", "ui_text_hash": hash("old"), "element_count": 5}
        mock_state_provider.get_state.return_value = _make_ui_state("new")
        mock_driver._get_current_app.return_value = "com.example.app"

        result = await verifier.verify(pre_state, "click")
        assert result.verified is True
        assert result.ui_tree_changed is True
        assert result.package_changed is False

    @pytest.mark.asyncio
    async def test_verify_navigation_package_changed(self, verifier, mock_state_provider, mock_driver):
        """Navigation action with package change verifies True."""
        pre_state = {"package": "com.example.app", "ui_text_hash": hash("same"), "element_count": 5}
        mock_state_provider.get_state.return_value = _make_ui_state("same")
        mock_driver._get_current_app.return_value = "com.other.app"

        result = await verifier.verify(pre_state, "back")
        assert result.verified is True
        assert result.package_changed is True

    @pytest.mark.asyncio
    async def test_verify_navigation_no_change(self, verifier, mock_state_provider, mock_driver):
        """Navigation action without state change verifies False."""
        text_hash = hash("same")
        pre_state = {"package": "com.example.app", "ui_text_hash": text_hash, "element_count": 5}
        mock_state_provider.get_state.return_value = _make_ui_state("same")
        mock_driver._get_current_app.return_value = "com.example.app"

        result = await verifier.verify(pre_state, "click")
        assert result.verified is False
        assert result.ui_tree_changed is False
        assert result.package_changed is False

    @pytest.mark.asyncio
    async def test_verify_non_navigation_no_change_ok(self, verifier, mock_state_provider, mock_driver):
        """Non-navigation action without change verifies True."""
        text_hash = hash("same")
        pre_state = {"package": "com.example.app", "ui_text_hash": text_hash, "element_count": 5}
        mock_state_provider.get_state.return_value = _make_ui_state("same")
        mock_driver._get_current_app.return_value = "com.example.app"

        result = await verifier.verify(pre_state, "scroll")
        assert result.verified is True

    @pytest.mark.asyncio
    async def test_capture_pre_state_exception(self, verifier, mock_state_provider, mock_driver):
        """Exception during capture returns empty dict."""
        mock_state_provider.get_state.side_effect = Exception("fail")
        state = await verifier.capture_pre_state()
        assert state == {}

    @pytest.mark.asyncio
    async def test_verify_empty_pre_state(self, verifier, mock_state_provider, mock_driver):
        """Empty pre_state skips verification with verified=True."""
        result = await verifier.verify({}, "click")
        assert result.verified is True
        assert "unavailable" in result.details

    @pytest.mark.asyncio
    async def test_capture_pre_state_uses_latest_state_without_live_get_state(
        self, mock_state_provider, mock_driver
    ):
        """Cached Manager state is used as pre-state in expensive parser mode."""
        latest_state = _make_ui_state("cached", [1, 2])
        mock_driver._get_current_app.return_value = "com.example.app"
        verifier = ActionVerifier(
            state_provider=mock_state_provider,
            driver=mock_driver,
            latest_state_provider=lambda: latest_state,
            expensive_state_capture=True,
        )

        state = await verifier.capture_pre_state()

        assert state["element_count"] == 2
        assert state["ui_text_hash"] == hash("cached")
        mock_state_provider.get_state.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verify_expensive_mode_defers_post_parsed_state(
        self, mock_state_provider, mock_driver
    ):
        """Post-action verification avoids a second OmniParser parse in expensive mode."""
        mock_driver._get_current_app.return_value = "com.example.app"
        verifier = ActionVerifier(
            state_provider=mock_state_provider,
            driver=mock_driver,
            latest_state_provider=lambda: None,
            expensive_state_capture=True,
        )

        result = await verifier.verify(
            {"package": "com.example.app", "ui_text_hash": hash("old"), "element_count": 1},
            "tap",
        )

        assert result.verified is True
        assert "parsed_state_deferred=True" in result.details
        mock_state_provider.get_state.assert_not_awaited()
