"""Tests for prompt builder."""

from unittest.mock import Mock

from mobile_crawler.domain.prompt_builder import PromptBuilder


class TestPromptBuilder:
    """Test PromptBuilder."""

    def test_build_system_prompt_no_form_data_or_account(self):
        """No form fill data and no App Account: prompt says so plainly."""
        config_manager = Mock()
        config_manager.get.return_value = None
        config_manager.user_config_store = Mock()
        config_manager.user_config_store.get_setting.return_value = None

        builder = PromptBuilder(config_manager, Mock())
        prompt = builder.build_system_prompt("com.a")

        assert "You are an AI-powered Android app exploration agent" in prompt
        assert "No App Account exists for com.a" in prompt

    def test_build_system_prompt_with_form_data(self):
        """Form Fill Data (address, email, phone) still reaches the prompt."""
        config_manager = Mock()
        config_manager.get.side_effect = lambda key, default=None: {
            "test_address": "Kaiserstraße 12, 60311 Frankfurt am Main, Germany",
            "test_email": "real_email@example.com",
            "test_phone": "+49 170 1234567",
        }.get(key, default)
        config_manager.user_config_store.get_setting.return_value = None

        builder = PromptBuilder(config_manager, Mock())
        prompt = builder.build_system_prompt("com.a")

        assert "Address: Kaiserstraße 12, 60311 Frankfurt am Main, Germany" in prompt
        assert "Email: real_email@example.com" in prompt
        assert "Phone Number: +49 170 1234567" in prompt

    def test_build_system_prompt_uses_only_current_packages_account(self, tmp_path):
        from mobile_crawler.config.config_manager import ConfigManager
        from mobile_crawler.infrastructure.app_account_store import AppAccount, AppAccountStore
        from mobile_crawler.infrastructure.user_config_store import UserConfigStore

        ucs = UserConfigStore(tmp_path / "u.db")
        ucs.create_schema()
        accounts = AppAccountStore(ucs)
        accounts.save("com.a", AppAccount("alice", "pw-a"))
        accounts.save("com.b", AppAccount("bob", "pw-b"))
        builder = PromptBuilder(ConfigManager(ucs), Mock())

        prompt_a = builder.build_system_prompt("com.a")
        prompt_b = builder.build_system_prompt("com.b")
        prompt_c = builder.build_system_prompt("com.c")

        assert "Username: alice" in prompt_a and "Password: pw-a" in prompt_a
        assert "bob" not in prompt_a and "pw-b" not in prompt_a
        assert "Username: bob" in prompt_b and "alice" not in prompt_b
        assert "No App Account exists for com.c" in prompt_c
        assert "testuser" not in prompt_c and "Password123" not in prompt_c
        ucs.close()

    def test_build_user_prompt_basic(self):
        """Test basic user prompt building."""
        config_manager = Mock()
        step_log_repo = Mock()
        step_log_repo.get_exploration_journal.return_value = []
        step_log_repo.get_step_statistics.return_value = {"total_steps": 0, "successful_steps": 0, "failed_steps": 0}

        builder = PromptBuilder(config_manager, step_log_repo)
        prompt = builder.build_user_prompt("base64screenshot", 1)

        assert '"screenshot": "base64screenshot"' in prompt
        assert '"exploration_journal": []' in prompt
        assert '"is_stuck": false' in prompt
        assert '"stuck_reason": null' in prompt
        assert '"available_actions"' in prompt

    def test_build_user_prompt_with_journal(self):
        """Test user prompt building with exploration journal."""
        from datetime import datetime

        from mobile_crawler.infrastructure.step_log_repository import StepLog

        config_manager = Mock()
        step_log_repo = Mock()

        # Create mock step logs
        step_log = StepLog(
            id=1,
            run_id=1,
            step_number=1,
            timestamp=datetime.now(),
            from_screen_id=None,
            to_screen_id=1,
            action_type="click",
            action_description="Clicked login button",
            target_bbox_json=None,
            input_text=None,
            execution_success=True,
            error_message=None,
            action_duration_ms=100.0,
            ai_response_time_ms=200.0,
            ai_reasoning="Login button visible",
        )
        step_log_repo.get_exploration_journal.return_value = [step_log]
        step_log_repo.get_step_statistics.return_value = {"total_steps": 1, "successful_steps": 1, "failed_steps": 0}

        builder = PromptBuilder(config_manager, step_log_repo)
        prompt = builder.build_user_prompt("base64screenshot", 1)

        assert '"step": 1' in prompt
        assert '"action": "Clicked login button"' in prompt
        assert '"outcome": "Success"' in prompt
        assert '"screen": "Screen #1"' in prompt

    def test_build_user_prompt_stuck(self):
        """Test user prompt building when stuck."""
        config_manager = Mock()
        step_log_repo = Mock()
        step_log_repo.get_exploration_journal.return_value = []
        step_log_repo.get_step_statistics.return_value = {"total_steps": 5, "successful_steps": 3, "failed_steps": 2}

        builder = PromptBuilder(config_manager, step_log_repo)
        prompt = builder.build_user_prompt("base64screenshot", 1, is_stuck=True, stuck_reason="Same screen 3 times")

        assert '"is_stuck": true' in prompt
        assert '"stuck_reason": "Same screen 3 times"' in prompt

    def test_build_user_prompt_with_screen_context(self):
        """Test user prompt building with screen context for novelty signals."""
        config_manager = Mock()
        step_log_repo = Mock()
        step_log_repo.get_exploration_journal.return_value = []
        step_log_repo.get_step_statistics.return_value = {"total_steps": 5, "successful_steps": 5, "failed_steps": 0}

        builder = PromptBuilder(config_manager, step_log_repo)
        prompt = builder.build_user_prompt(
            screenshot_b64="base64screenshot",
            run_id=1,
            is_stuck=False,
            current_screen_id=5,
            current_screen_is_new=True,
            total_unique_screens=3,
        )

        assert '"current_screen_id": 5' in prompt
        assert "NEW" in prompt
        assert '"unique_screens_discovered": 3' in prompt

    def test_get_available_actions(self):
        """Test that all expected actions are available."""
        config_manager = Mock()
        step_log_repo = Mock()

        builder = PromptBuilder(config_manager, step_log_repo)
        actions = builder._get_available_actions()

        expected_actions = [
            "click",
            "input",
            "long_press",
            "scroll_up",
            "scroll_down",
            "scroll_left",
            "scroll_right",
            "back",
        ]

        for action in expected_actions:
            assert action in actions
            assert isinstance(actions[action], str)
            assert len(actions[action]) > 0

    def test_get_exploration_journal_formatting(self):
        """Test exploration journal formatting with novelty signals."""
        from datetime import datetime

        from mobile_crawler.infrastructure.step_log_repository import StepLog

        config_manager = Mock()
        step_log_repo = Mock()

        # Create mock step logs
        step1 = StepLog(
            id=1,
            run_id=1,
            step_number=1,
            timestamp=datetime.now(),
            from_screen_id=None,
            to_screen_id=1,
            action_type="click",
            action_description="Clicked button",
            target_bbox_json=None,
            input_text=None,
            execution_success=True,
            error_message=None,
            action_duration_ms=100.0,
            ai_response_time_ms=200.0,
            ai_reasoning=None,
        )

        step2 = StepLog(
            id=2,
            run_id=1,
            step_number=2,
            timestamp=datetime.now(),
            from_screen_id=1,
            to_screen_id=1,  # Same screen - revisit
            action_type="input",
            action_description="Entered text",
            target_bbox_json=None,
            input_text="test",
            execution_success=False,
            error_message="Element not found",
            action_duration_ms=50.0,
            ai_response_time_ms=150.0,
            ai_reasoning=None,
        )

        # Return in chronological order (as the repo does after reversing)
        step_log_repo.get_exploration_journal.return_value = [step1, step2]

        builder = PromptBuilder(config_manager, step_log_repo)
        journal = builder._get_exploration_journal(1)

        assert len(journal) == 2
        # First entry should be step 1, marked as NEW (first time seeing screen 1)
        assert journal[0]["step"] == 1
        assert journal[0]["outcome"] == "Success"
        assert journal[0]["screen_status"] == "NEW"
        # Second entry should be step 2, marked as revisited (same screen 1)
        assert journal[1]["step"] == 2
        assert "Failed: Element not found" in journal[1]["outcome"]
        assert journal[1]["screen_status"] == "revisited"

    def test_get_exploration_hint_new_screen(self):
        """Test exploration hint for new screen discovery."""
        config_manager = Mock()
        step_log_repo = Mock()

        builder = PromptBuilder(config_manager, step_log_repo)
        hint = builder._get_exploration_hint(0.5, current_screen_is_new=True)

        assert "discovered a new screen" in hint.lower()

    def test_get_exploration_hint_low_efficiency(self):
        """Test exploration hint for low discovery efficiency."""
        config_manager = Mock()
        step_log_repo = Mock()

        builder = PromptBuilder(config_manager, step_log_repo)
        hint = builder._get_exploration_hint(0.2, current_screen_is_new=False)

        assert "Low discovery" in hint or "different actions" in hint
