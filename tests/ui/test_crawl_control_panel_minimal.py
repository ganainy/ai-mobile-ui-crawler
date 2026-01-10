"""Minimal test to isolate PySide6 issue."""
import pytest
from unittest.mock import Mock
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Signal

# Ensure QApplication exists
@pytest.fixture(scope="module")
def app():
    """Create QApplication instance for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_qwidget_creation(app):
    """Test that QWidget can be created."""
    widget = QWidget()
    assert widget is not None
    widget.deleteLater()


def test_signal_creation(app):
    """Test that Signal can be created."""
    class TestWidget(QWidget):
        test_signal = Signal()
    
    widget = TestWidget()
    assert widget is not None
    widget.deleteLater()


def test_button_creation(app):
    """Test that QPushButton can be created."""
    from PySide6.QtWidgets import QPushButton
    button = QPushButton("Test")
    assert button is not None
    button.deleteLater()


def test_crawl_control_panel_import(app):
    """Test that CrawlControlPanel can be imported."""
    from mobile_crawler.ui.widgets.crawl_control_panel import CrawlControlPanel
    assert CrawlControlPanel is not None


def test_crawl_control_panel_creation(app):
    """Test that CrawlControlPanel can be created."""
    from mobile_crawler.ui.widgets.crawl_control_panel import CrawlControlPanel
    from mobile_crawler.core.crawl_state_machine import CrawlState
    
    mock_controller = Mock()
    mock_controller.get_state = Mock(return_value=CrawlState.UNINITIALIZED)
    
    panel = CrawlControlPanel(crawl_controller=mock_controller)
    assert panel is not None
    panel.deleteLater()
