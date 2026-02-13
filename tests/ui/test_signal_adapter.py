"""Tests for QtSignalAdapter."""

import pytest

from PySide6.QtCore import QObject, Signal


@pytest.fixture
def qt_app():
    """Create QApplication instance for all UI tests.
    
    This fixture is created at session scope to ensure QApplication
    exists for all UI tests. PySide6 requires exactly one QApplication
    instance to exist for widgets to work properly.
    """
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def _create_signal_adapter():
    """Create a new QtSignalAdapter instance for testing.
    
    Returns:
        QtSignalAdapter instance
    """
    from mobile_crawler.ui.signal_adapter import QtSignalAdapter
    return QtSignalAdapter()


class TestQtSignalAdapterInit:
    """Tests for QtSignalAdapter initialization."""

    def test_initialization(self, qt_app):
        """Test that QtSignalAdapter initializes correctly."""
        adapter = _create_signal_adapter()
        assert adapter is not None
        assert isinstance(adapter, QObject)

    def test_has_all_signals(self, qt_app):
        """Test that all required signals exist."""
        adapter = _create_signal_adapter()
        assert hasattr(adapter, 'crawl_started')
        assert hasattr(adapter, 'step_started')
        assert hasattr(adapter, 'screenshot_captured')
        assert hasattr(adapter, 'ai_request_sent')
        assert hasattr(adapter, 'ai_response_received')
        assert hasattr(adapter, 'action_executed')
        assert hasattr(adapter, 'step_completed')
        assert hasattr(adapter, 'crawl_completed')
        assert hasattr(adapter, 'error_occurred')
        assert hasattr(adapter, 'state_changed')

    def test_signals_are_signal_instances(self, qt_app):
        """Test that all attributes are Signal instances."""
        adapter = _create_signal_adapter()
        assert isinstance(adapter.crawl_started, Signal)
        assert isinstance(adapter.step_started, Signal)
        assert isinstance(adapter.screenshot_captured, Signal)
        assert isinstance(adapter.ai_request_sent, Signal)
        assert isinstance(adapter.ai_response_received, Signal)
        assert isinstance(adapter.action_executed, Signal)
        assert isinstance(adapter.step_completed, Signal)
        assert isinstance(adapter.crawl_completed, Signal)
        assert isinstance(adapter.error_occurred, Signal)
        assert isinstance(adapter.state_changed, Signal)


class TestCrawlStarted:
    """Tests for on_crawl_started method."""

    def test_on_crawl_started_emits_signal(self, qt_app):
        """Test that on_crawl_started emits crawl_started signal."""
        adapter = _create_signal_adapter()
        
        signal_emitted = False
        emitted_run_id = None
        emitted_package = None
        
        def on_crawl_started(run_id, target_package):
            nonlocal signal_emitted, emitted_run_id, emitted_package
            signal_emitted = True
            emitted_run_id = run_id
            emitted_package = target_package
        
        adapter.crawl_started.connect(on_crawl_started)
        
        # Call the method
        adapter.on_crawl_started(123, "com.example.app")
        
        assert signal_emitted
        assert emitted_run_id == 123
        assert emitted_package == "com.example.app"


class TestStepStarted:
    """Tests for on_step_started method."""

    def test_on_step_started_emits_signal(self, qt_app):
        """Test that on_step_started emits step_started signal."""
        adapter = _create_signal_adapter()
        
        signal_emitted = False
        emitted_run_id = None
        emitted_step_number = None
        
        def on_step_started(run_id, step_number):
            nonlocal signal_emitted, emitted_run_id, emitted_step_number
            signal_emitted = True
            emitted_run_id = run_id
            emitted_step_number = step_number
        
        adapter.step_started.connect(on_step_started)
        
        # Call the method
        adapter.on_step_started(123, 5)
        
        assert signal_emitted
        assert emitted_run_id == 123
        assert emitted_step_number == 5


class TestScreenshotCaptured:
    """Tests for on_screenshot_captured method."""

    def test_on_screenshot_captured_emits_signal(self, qt_app):
        """Test that on_screenshot_captured emits screenshot_captured signal."""
        adapter = _create_signal_adapter()
        
        signal_emitted = False
        emitted_run_id = None
        emitted_step_number = None
        emitted_path = None
        
        def on_screenshot_captured(run_id, step_number, screenshot_path):
            nonlocal signal_emitted, emitted_run_id, emitted_step_number, emitted_path
            signal_emitted = True
            emitted_run_id = run_id
            emitted_step_number = step_number
            emitted_path = screenshot_path
        
        adapter.screenshot_captured.connect(on_screenshot_captured)
        
        # Call the method
        adapter.on_screenshot_captured(123, 5, "/path/to/screenshot.png")
        
        assert signal_emitted
        assert emitted_run_id == 123
        assert emitted_step_number == 5
        assert emitted_path == "/path/to/screenshot.png"


class TestAIRequestSent:
    """Tests for on_ai_request_sent method."""

    def test_on_ai_request_sent_emits_signal(self, qt_app):
        """Test that on_ai_request_sent emits ai_request_sent signal."""
        adapter = _create_signal_adapter()
        
        signal_emitted = False
        emitted_run_id = None
        emitted_step_number = None
        emitted_data = None
        
        def on_ai_request_sent(run_id, step_number, request_data):
            nonlocal signal_emitted, emitted_run_id, emitted_step_number, emitted_data
            signal_emitted = True
            emitted_run_id = run_id
            emitted_step_number = step_number
            emitted_data = request_data
        
        adapter.ai_request_sent.connect(on_ai_request_sent)
        
        # Call the method
        request_data = {"prompt": "test", "image": "base64..."}
        adapter.on_ai_request_sent(123, 5, request_data)
        
        assert signal_emitted
        assert emitted_run_id == 123
        assert emitted_step_number == 5
        assert emitted_data == request_data


class TestAIResponseReceived:
    """Tests for on_ai_response_received method."""

    def test_on_ai_response_received_emits_signal(self, qt_app):
        """Test that on_ai_response_received emits ai_response_received signal."""
        adapter = _create_signal_adapter()
        
        signal_emitted = False
        emitted_run_id = None
        emitted_step_number = None
        emitted_data = None
        
        def on_ai_response_received(run_id, step_number, response_data):
            nonlocal signal_emitted, emitted_run_id, emitted_step_number, emitted_data
            signal_emitted = True
            emitted_run_id = run_id
            emitted_step_number = step_number
            emitted_data = response_data
        
        adapter.ai_response_received.connect(on_ai_response_received)
        
        # Call the method
        response_data = {"actions": [], "signup_completed": False}
        adapter.on_ai_response_received(123, 5, response_data)
        
        assert signal_emitted
        assert emitted_run_id == 123
        assert emitted_step_number == 5
        assert emitted_data == response_data


class TestActionExecuted:
    """Tests for on_action_executed method."""

    def test_on_action_executed_emits_signal(self, qt_app):
        """Test that on_action_executed emits action_executed signal."""
        adapter = _create_signal_adapter()
        
        signal_emitted = False
        emitted_run_id = None
        emitted_step_number = None
        emitted_action_index = None
        emitted_result = None
        
        def on_action_executed(run_id, step_number, action_index, result):
            nonlocal signal_emitted, emitted_run_id, emitted_step_number, emitted_action_index, emitted_result
            signal_emitted = True
            emitted_run_id = run_id
            emitted_step_number = step_number
            emitted_action_index = action_index
            emitted_result = result
        
        adapter.action_executed.connect(on_action_executed)
        
        # Call the method
        from mobile_crawler.domain.models import ActionResult
        result = ActionResult(
            success=True,
            action_type="click",
            target="button",
            duration_ms=100.5,
            error_message=None,
            navigated_away=True
        )
        adapter.on_action_executed(123, 5, 0, result)
        
        assert signal_emitted
        assert emitted_run_id == 123
        assert emitted_step_number == 5
        assert emitted_action_index == 0
        assert emitted_result.success is True


class TestStepCompleted:
    """Tests for on_step_completed method."""

    def test_on_step_completed_emits_signal(self, qt_app):
        """Test that on_step_completed emits step_completed signal."""
        adapter = _create_signal_adapter()
        
        signal_emitted = False
        emitted_run_id = None
        emitted_step_number = None
        emitted_actions_count = None
        emitted_duration = None
        
        def on_step_completed(run_id, step_number, actions_count, duration_ms):
            nonlocal signal_emitted, emitted_run_id, emitted_step_number, emitted_actions_count, emitted_duration
            signal_emitted = True
            emitted_run_id = run_id
            emitted_step_number = step_number
            emitted_actions_count = actions_count
            emitted_duration = duration_ms
        
        adapter.step_completed.connect(on_step_completed)
        
        # Call the method
        adapter.on_step_completed(123, 5, 3, 1500.5)
        
        assert signal_emitted
        assert emitted_run_id == 123
        assert emitted_step_number == 5
        assert emitted_actions_count == 3
        assert emitted_duration == 1500.5


class TestCrawlCompleted:
    """Tests for on_crawl_completed method."""

    def test_on_crawl_completed_emits_signal(self, qt_app):
        """Test that on_crawl_completed emits crawl_completed signal."""
        adapter = _create_signal_adapter()
        
        signal_emitted = False
        emitted_run_id = None
        emitted_total_steps = None
        emitted_duration = None
        emitted_reason = None
        
        def on_crawl_completed(run_id, total_steps, total_duration_ms, reason):
            nonlocal signal_emitted, emitted_run_id, emitted_total_steps, emitted_duration, emitted_reason
            signal_emitted = True
            emitted_run_id = run_id
            emitted_total_steps = total_steps
            emitted_duration = total_duration_ms
            emitted_reason = reason
        
        adapter.crawl_completed.connect(on_crawl_completed)
        
        # Call the method
        adapter.on_crawl_completed(123, 50, 60000.0, "Max steps reached")
        
        assert signal_emitted
        assert emitted_run_id == 123
        assert emitted_total_steps == 50
        assert emitted_duration == 60000.0
        assert emitted_reason == "Max steps reached"


class TestErrorOccurred:
    """Tests for on_error method."""

    def test_on_error_emits_signal(self, qt_app):
        """Test that on_error emits error_occurred signal."""
        adapter = _create_signal_adapter()
        
        signal_emitted = False
        emitted_run_id = None
        emitted_step_number = None
        emitted_error = None
        
        def on_error_occurred(run_id, step_number, error):
            nonlocal signal_emitted, emitted_run_id, emitted_step_number, emitted_error
            signal_emitted = True
            emitted_run_id = run_id
            emitted_step_number = step_number
            emitted_error = error
        
        adapter.error_occurred.connect(on_error_occurred)
        
        # Call the method with step_number
        error = Exception("Test error")
        adapter.on_error(123, 5, error)
        
        assert signal_emitted
        assert emitted_run_id == 123
        assert emitted_step_number == 5
        assert str(emitted_error) == "Test error"

    def test_on_error_with_none_step_number(self, qt_app):
        """Test that on_error handles None step_number."""
        adapter = _create_signal_adapter()
        
        signal_emitted = False
        emitted_step_number = None
        
        def on_error_occurred(run_id, step_number, error):
            nonlocal signal_emitted, emitted_step_number
            signal_emitted = True
            emitted_step_number = step_number
        
        adapter.error_occurred.connect(on_error_occurred)
        
        # Call the method with None step_number
        error = Exception("Test error")
        adapter.on_error(123, None, error)
        
        assert signal_emitted
        # Should use -1 when step_number is None
        assert emitted_step_number == -1


class TestStateChanged:
    """Tests for on_state_changed method."""

    def test_on_state_changed_emits_signal(self, qt_app):
        """Test that on_state_changed emits state_changed signal."""
        adapter = _create_signal_adapter()
        
        signal_emitted = False
        emitted_run_id = None
        emitted_old_state = None
        emitted_new_state = None
        
        def on_state_changed(run_id, old_state, new_state):
            nonlocal signal_emitted, emitted_run_id, emitted_old_state, emitted_new_state
            signal_emitted = True
            emitted_run_id = run_id
            emitted_old_state = old_state
            emitted_new_state = new_state
        
        adapter.state_changed.connect(on_state_changed)
        
        # Call the method
        adapter.on_state_changed(123, "RUNNING", "STOPPED")
        
        assert signal_emitted
        assert emitted_run_id == 123
        assert emitted_old_state == "RUNNING"
        assert emitted_new_state == "STOPPED"


class TestMultipleConnections:
    """Tests for multiple signal connections."""

    def test_multiple_connections_to_same_signal(self, qt_app):
        """Test that multiple connections to the same signal work."""
        adapter = _create_signal_adapter()
        
        call_count = 0
        
        def handler1(run_id, package):
            nonlocal call_count
            call_count += 1
        
        def handler2(run_id, package):
            nonlocal call_count
            call_count += 1
        
        adapter.crawl_started.connect(handler1)
        adapter.crawl_started.connect(handler2)
        
        # Call the method
        adapter.on_crawl_started(123, "com.example.app")
        
        # Both handlers should be called
        assert call_count == 2
