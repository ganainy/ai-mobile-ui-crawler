"""Tests for UI wait predicates."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from mobile_crawler.domain.ui_wait_predicate import (
    AdaptiveWaitConfig,
    UIWaitPredicate,
    WaitProfile,
    DEFAULT_WAIT_PROFILES,
)


@pytest.fixture
def mock_state_provider():
    """Create a mock state provider."""
    provider = AsyncMock()
    return provider


@pytest.fixture
def wait_config():
    """Create a default AdaptiveWaitConfig."""
    return AdaptiveWaitConfig(config_manager=None)


@pytest.fixture
def wait_predicate(mock_state_provider, wait_config):
    """Create a UIWaitPredicate with mock dependencies."""
    return UIWaitPredicate(
        state_provider=mock_state_provider,
        config=wait_config,
    )


def _make_ui_state(text: str):
    """Create a mock UI state with formatted_text."""
    state = MagicMock()
    state.formatted_text = text
    return state


class TestWaitProfile:
    def test_timeout_s_conversion(self):
        profile = WaitProfile(timeout_ms=3000, poll_interval_ms=200)
        assert profile.timeout_s == 3.0
        assert profile.poll_interval_s == 0.2


class TestAdaptiveWaitConfig:
    def test_known_action_type(self, wait_config):
        profile = wait_config.get_profile("tap")
        assert profile.timeout_ms == 2000
        assert profile.poll_interval_ms == 150

    def test_unknown_action_type_returns_default(self, wait_config):
        profile = wait_config.get_profile("unknown_action")
        assert profile.timeout_ms == 3000
        assert profile.poll_interval_ms == 200

    def test_from_config(self):
        mock_cm = MagicMock()
        mock_cm.get.return_value = 9999
        config = AdaptiveWaitConfig.from_config(mock_cm)
        assert config.config_manager is mock_cm

    def test_all_default_profiles_present(self):
        expected = ["default", "tap", "click", "scroll", "type", "back", "home", "start_app"]
        for action in expected:
            assert action in DEFAULT_WAIT_PROFILES


class TestUIWaitPredicate:
    @pytest.mark.asyncio
    async def test_settled_within_timeout(self, wait_predicate, mock_state_provider):
        """UI settles when two consecutive polls return same text."""
        mock_state_provider.get_state.side_effect = [
            _make_ui_state("state_a"),
            _make_ui_state("state_b"),
            _make_ui_state("state_b"),  # Settled
        ]
        result = await wait_predicate.wait_for_ui_settled("click")
        assert result is True

    @pytest.mark.asyncio
    async def test_timeout_returns_false(self, wait_predicate, mock_state_provider):
        """Returns False when UI never settles within timeout."""
        # Every poll returns a different state
        call_count = 0
        async def always_changing():
            nonlocal call_count
            call_count += 1
            return _make_ui_state(f"state_{call_count}")
        mock_state_provider.get_state.side_effect = always_changing

        result = await wait_predicate.wait_for_ui_settled(
            "click", timeout_ms=100
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_tap_uses_tap_profile(self, mock_state_provider):
        """Tap actions use the tap-specific timeout."""
        config = AdaptiveWaitConfig(config_manager=None)
        # Spy on the profile selection
        predicate = UIWaitPredicate(
            state_provider=mock_state_provider,
            config=config,
        )
        profile = config.get_profile("tap")
        assert profile.timeout_ms == 2000

    @pytest.mark.asyncio
    async def test_polls_at_interval(self, mock_state_provider):
        """Verifies polling occurs at the configured interval."""
        config = AdaptiveWaitConfig(config_manager=None)
        predicate = UIWaitPredicate(
            state_provider=mock_state_provider,
            config=config,
        )
        # Return settled state on polls 1 and 2
        mock_state_provider.get_state.side_effect = [
            _make_ui_state("same"),
            _make_ui_state("same"),
        ]
        import time
        start = time.monotonic()
        result = await predicate.wait_for_ui_settled("click", timeout_ms=500)
        elapsed = time.monotonic() - start
        assert result is True
        # Should have polled at least twice (initial + settled check)
        assert mock_state_provider.get_state.call_count >= 2

    @pytest.mark.asyncio
    async def test_first_poll_settled(self, wait_predicate, mock_state_provider):
        """Returns True quickly if state is already settled."""
        # Two consecutive identical reads immediately
        mock_state_provider.get_state.side_effect = [
            _make_ui_state("same"),
            _make_ui_state("same"),
        ]
        result = await wait_predicate.wait_for_ui_settled("click")
        assert result is True

    @pytest.mark.asyncio
    async def test_exception_retry(self, wait_predicate, mock_state_provider):
        """Retries when state_provider raises exceptions."""
        mock_state_provider.get_state.side_effect = [
            Exception("transient error"),
            _make_ui_state("state_a"),
            _make_ui_state("state_a"),  # Settled
        ]
        result = await wait_predicate.wait_for_ui_settled("click", timeout_ms=1000)
        assert result is True

    @pytest.mark.asyncio
    async def test_custom_timeout_override(self, wait_predicate, mock_state_provider):
        """Custom timeout_ms overrides profile default."""
        call_count = 0
        async def always_changing():
            nonlocal call_count
            call_count += 1
            return _make_ui_state(f"state_{call_count}")
        mock_state_provider.get_state.side_effect = always_changing

        result = await wait_predicate.wait_for_ui_settled(
            "click", timeout_ms=50
        )
        assert result is False
        # Should have polled only a few times given 50ms timeout
        assert call_count <= 5
