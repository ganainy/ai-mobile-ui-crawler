import threading
import time

from PySide6.QtCore import QCoreApplication

from mobile_crawler.domain.human_fallback import HumanReply, HumanRequest, RequestKind
from mobile_crawler.ui.human_fallback_dialog import HumanFallbackDialog, QtHumanPrompter


def _pump(qtbot, cond, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end and not cond():
        QCoreApplication.processEvents()
        time.sleep(0.01)
    return cond()


def _run_prompter(prompter, request, timeout):
    result = {}
    t = threading.Thread(target=lambda: result.setdefault("r", prompter(request, timeout)))
    t.start()
    return t, result


def _active_dialog():
    from PySide6.QtWidgets import QApplication

    return next((w for w in QApplication.topLevelWidgets() if isinstance(w, HumanFallbackDialog) and w.isVisible()), None)


def test_code_answered_from_crawl_thread_without_blocking_gui(qtbot):
    prompter = QtHumanPrompter()
    t, result = _run_prompter(prompter, HumanRequest(RequestKind.CODE, "code?"), 10)
    assert _pump(qtbot, lambda: _active_dialog() is not None)
    dlg = _active_dialog()
    dlg.code_input.setText("424242")
    dlg.continue_button.click()
    t.join(3)
    assert result["r"] == HumanReply(code="424242")


def test_manual_step_continue(qtbot):
    prompter = QtHumanPrompter()
    t, result = _run_prompter(prompter, HumanRequest(RequestKind.MANUAL_STEP, "finish"), 10)
    assert _pump(qtbot, lambda: _active_dialog() is not None)
    _active_dialog().continue_button.click()
    t.join(3)
    assert result["r"] == HumanReply(code=None)


def test_timeout_returns_none_and_closes_dialog(qtbot):
    prompter = QtHumanPrompter()
    t, result = _run_prompter(prompter, HumanRequest(RequestKind.CODE, "code?"), 0.3)
    assert _pump(qtbot, lambda: _active_dialog() is not None)
    t.join(3)
    assert result["r"] is None
    assert _pump(qtbot, lambda: _active_dialog() is None)


def test_skip_button(qtbot):
    prompter = QtHumanPrompter()
    t, result = _run_prompter(prompter, HumanRequest(RequestKind.CODE, "code?"), 10)
    assert _pump(qtbot, lambda: _active_dialog() is not None)
    _active_dialog().skip_button.click()
    t.join(3)
    assert result["r"] == HumanReply(skipped=True)
