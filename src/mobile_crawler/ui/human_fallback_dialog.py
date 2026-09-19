"""Qt bridge for Human Fallback: shows a non-blocking dialog on the GUI thread.

The crawl thread calls the prompter, which emits a signal to the GUI thread and waits on a
threading.Event with the timeout. The GUI event loop is never blocked: the dialog is shown
with open(), not exec().
"""

import threading

from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from mobile_crawler.domain.human_fallback import HumanReply, HumanRequest, RequestKind


class _Pending:
    def __init__(self, request: HumanRequest):
        self.request = request
        self.done = threading.Event()
        self.reply: HumanReply | None = None
        self.dialog: QDialog | None = None


class HumanFallbackDialog(QDialog):
    def __init__(self, request: HumanRequest, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Human help needed")
        self.setModal(False)
        self._is_code = request.kind is RequestKind.CODE
        self.reply: HumanReply | None = None

        layout = QVBoxLayout(self)
        label = QLabel(request.message)
        label.setWordWrap(True)
        layout.addWidget(label)
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Verification code")
        self.code_input.setVisible(self._is_code)
        layout.addWidget(self.code_input)

        buttons = QDialogButtonBox()
        self.continue_button = buttons.addButton(
            "Submit code" if self._is_code else "Continue", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.skip_button = buttons.addButton("Skip authentication", QDialogButtonBox.ButtonRole.RejectRole)
        self.continue_button.clicked.connect(self._on_continue)
        self.skip_button.clicked.connect(self._on_skip)
        layout.addWidget(buttons)

    def _on_continue(self):
        code = self.code_input.text().strip() if self._is_code else None
        if self._is_code and not code:
            return
        self.reply = HumanReply(code=code)
        self.accept()

    def _on_skip(self):
        self.reply = HumanReply(skipped=True)
        self.reject()

    def reject(self):
        # Closing the window counts as skipping
        if self.reply is None:
            self.reply = HumanReply(skipped=True)
        super().reject()


class QtHumanPrompter(QObject):
    """HumanPrompter implementation; create on the GUI thread, call from the crawl thread."""

    _show_requested = Signal(object)
    _timeout_requested = Signal(object)

    def __init__(self, parent_widget: QWidget | None = None):
        super().__init__(parent_widget)
        self._parent_widget = parent_widget
        self._show_requested.connect(self._show, Qt.ConnectionType.QueuedConnection)
        self._timeout_requested.connect(self._close_on_timeout, Qt.ConnectionType.QueuedConnection)

    def __call__(self, request: HumanRequest, timeout_seconds: float) -> HumanReply | None:
        pending = _Pending(request)
        self._show_requested.emit(pending)
        if not pending.done.wait(timeout_seconds):
            self._timeout_requested.emit(pending)
            # If the user answered in the instant before the close was processed, honour it
            return pending.reply
        return pending.reply

    @Slot(object)
    def _show(self, pending: _Pending):
        dialog = HumanFallbackDialog(pending.request, self._parent_widget)
        pending.dialog = dialog

        def finished():
            if pending.reply is None:
                pending.reply = dialog.reply
            pending.done.set()

        dialog.finished.connect(lambda _code: finished())
        dialog.open()

    @Slot(object)
    def _close_on_timeout(self, pending: _Pending):
        if pending.dialog is not None and pending.dialog.isVisible():
            pending.dialog.reply = None
            pending.dialog.hide()
            pending.dialog.deleteLater()
