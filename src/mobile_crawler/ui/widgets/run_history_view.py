"""Run history view widget for mobile-crawler GUI."""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from mobile_crawler.domain.report_generator import ReportGenerator
    from mobile_crawler.infrastructure.mobsf_manager import MobSFManager
    from mobile_crawler.infrastructure.run_repository import RunRepository
    from mobile_crawler.infrastructure.run_stats_repository import RunStatsRepository


class MobSFAnalysisWorker(QThread):
    """Background worker for MobSF analysis."""

    analysis_finished = Signal(int, object)
    analysis_failed = Signal(int, str)

    def __init__(self, run, mobsf_manager: "MobSFManager"):
        super().__init__()
        self._run = run
        self._mobsf_manager = mobsf_manager

    def run(self):
        try:
            result = self._mobsf_manager.analyze_run(self._run, self._run.device_id)
            self.analysis_finished.emit(self._run.id, result)
        except Exception as e:
            self.analysis_failed.emit(self._run.id, str(e))


class RunStatsDialog(QDialog):
    """Read-only dialog rendering a persisted run_stats record, grouped by section."""

    def __init__(self, stats, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Run Statistics")
        self.resize(560, 620)

        layout = QVBoxLayout(self)

        # Group definitions: (section title, list of (display label, attr name))
        groups = [
            ("Crawl Progress", [
                ("Total Steps", "total_steps"),
                ("Successful Steps", "successful_steps"),
                ("Failed Steps", "failed_steps"),
                ("Duration (s)", "crawl_duration_seconds"),
                ("Avg Step (ms)", "avg_step_duration_ms"),
            ]),
            ("Screen Discovery", [
                ("Unique Screens", "unique_screens_visited"),
                ("Total Visits", "total_screen_visits"),
                ("Deepest Depth", "deepest_navigation_depth"),
                ("Unique Activities", "unique_activities_visited"),
            ]),
            ("Action Statistics", [
                ("Actions By Type", "actions_by_type"),
                ("Successful By Type", "successful_actions_by_type"),
                ("Failed By Type", "failed_actions_by_type"),
                ("Avg Duration (ms)", "avg_action_duration_ms"),
                ("Min Duration (ms)", "min_action_duration_ms"),
                ("Max Duration (ms)", "max_action_duration_ms"),
            ]),
            ("AI Performance", [
                ("Total AI Calls", "total_ai_calls"),
                ("Avg Response (ms)", "avg_ai_response_time_ms"),
                ("Min Response (ms)", "min_ai_response_time_ms"),
                ("Max Response (ms)", "max_ai_response_time_ms"),
                ("Timeouts", "ai_timeout_count"),
                ("Errors", "ai_error_count"),
                ("Retries", "ai_retry_count"),
                ("Invalid Responses", "invalid_response_count"),
                ("Total Tokens", "total_ai_tokens_used"),
                ("Vision Calls", "vision_call_count"),
                ("Non-Vision Calls", "non_vision_call_count"),
                ("AI Success By Type", "ai_success_by_type"),
                ("AI Total By Type", "ai_total_by_type"),
            ]),
            ("Batching", [
                ("Multi-Action Batches", "multi_action_batch_count"),
                ("Single Actions", "single_action_count"),
                ("Total Batch Actions", "total_batch_actions"),
                ("Avg Batch Size", "avg_batch_size"),
                ("Max Batch Size", "max_batch_size"),
            ]),
            ("Error & Recovery", [
                ("Stuck Detections", "stuck_detection_count"),
                ("Stuck Recoveries", "stuck_recovery_success"),
                ("App Crashes", "app_crash_count"),
                ("App Relaunches", "app_relaunch_count"),
                ("Context Losses", "context_loss_count"),
                ("Context Recoveries", "context_recovery_count"),
                ("Avg Recovery (ms)", "avg_recovery_time_ms"),
            ]),
            ("Device & App", [
                ("Device", "device_model"),
                ("Android Version", "android_version"),
                ("App Package", "app_package"),
                ("App Version", "app_version"),
            ]),
            ("Network & Security", [
                ("PCAP Size (bytes)", "pcap_file_size_bytes"),
                ("PCAP Packets", "pcap_packet_count"),
                ("MobSF Score", "mobsf_security_score"),
                ("MobSF High", "mobsf_high_issues"),
                ("MobSF Medium", "mobsf_medium_issues"),
                ("MobSF Low", "mobsf_low_issues"),
            ]),
            ("Coverage", [
                ("Transitions", "transition_count"),
                ("Unique Transitions", "unique_transitions"),
            ]),
        ]

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        for title, rows in groups:
            group = QGroupBox(title)
            grid = QGridLayout(group)
            for r, (label, attr) in enumerate(rows):
                value = format_stat_value(getattr(stats, attr, None))
                grid.addWidget(QLabel(f"<b>{label}</b>"), r, 0)
                grid.addWidget(QLabel(value), r, 1)
            content_layout.addWidget(group)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)


def format_stat_value(value) -> str:
    """Format a stat value for display."""
    if value is None:
        return "—"
    if isinstance(value, dict):
        if not value:
            return "—"
        return ", ".join(f"{k}: {v}" for k, v in value.items())
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


class RunHistoryView(QWidget):
    """Widget for viewing and managing past crawl runs.

    Displays a table of runs with metadata and provides actions
    for deleting runs, generating reports, and running MobSF analysis.
    """

    # Signals
    run_deleted = Signal(int)  # Emits run_id when a run is deleted
    report_generated = Signal(int)  # Emits run_id when a report is generated
    mobsf_completed = Signal(int)  # Emits run_id when MobSF analysis completes

    def __init__(
        self,
        run_repository: "RunRepository",
        report_generator: "ReportGenerator",
        mobsf_manager: "MobSFManager",
        run_stats_repository: "RunStatsRepository | None" = None,
        parent=None
    ):
        """Initialize run history view widget.

        Args:
            run_repository: RunRepository instance for fetching runs
            report_generator: ReportGenerator instance for generating reports
            mobsf_manager: MobSFManager instance for running MobSF analysis
            run_stats_repository: Optional RunStatsRepository for the View Stats action
            parent: Parent widget
        """
        super().__init__(parent)
        self._run_repository = run_repository
        self._report_generator = report_generator
        self._mobsf_manager = mobsf_manager
        self._run_stats_repository = run_stats_repository
        self._mobsf_worker = None

        self.setMinimumHeight(170)

        self._setup_ui()
        self._load_runs()

    def _setup_ui(self):
        """Set up user interface."""
        layout = QVBoxLayout()

        # Title label
        title_label = QLabel("Run History")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # Table for run metadata
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Device",
            "Package",
            "Start Time",
            "End Time",
            "Status",
            "Steps",
            "Screens",
            "Model",
            "Actions"
        ])

        # Configure table
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        # Make table read-only
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table)

        # Buttons row
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setToolTip("Reload the run list from the database")
        self.refresh_button.clicked.connect(self._load_runs)
        buttons_layout.addWidget(self.refresh_button)

        # Delete button
        self.delete_button = QPushButton("Delete Run")
        self.delete_button.setToolTip("Delete the selected run and all of its data")
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.delete_button.setEnabled(False)
        buttons_layout.addWidget(self.delete_button)

        # Generate Report button
        self.report_button = QPushButton("Generate Report")
        self.report_button.setToolTip("Generate an enhanced report for the selected run")
        self.report_button.clicked.connect(self._on_generate_report_clicked)
        self.report_button.setEnabled(False)
        buttons_layout.addWidget(self.report_button)

        # Run MobSF button
        self.mobsf_button = QPushButton("Run MobSF")
        self.mobsf_button.setToolTip("Run MobSF static analysis for the selected run's app")
        self.mobsf_button.clicked.connect(self._on_mobsf_clicked)
        self.mobsf_button.setEnabled(False)
        buttons_layout.addWidget(self.mobsf_button)

        # View Stats button
        self.stats_button = QPushButton("View Stats")
        self.stats_button.clicked.connect(self._on_view_stats_clicked)
        self.stats_button.setEnabled(False)
        self.stats_button.setToolTip("View detailed persisted statistics for the selected run")
        if not self._run_stats_repository:
            self.stats_button.hide()
        buttons_layout.addWidget(self.stats_button)

        layout.addLayout(buttons_layout)

        # Set the layout for this widget
        self.setLayout(layout)

        # Connect table selection change
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

    def _load_runs(self):
        """Load all runs from repository into table."""
        # Save current selection if any
        selected_id = self.get_selected_run_id()

        runs = self._run_repository.get_all_runs()

        self.table.setRowCount(len(runs))

        # Need session manager to resolve paths
        # We'll create it on fly since it's lightweight, or we could inject it
        from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager
        session_manager = SessionFolderManager()

        for row, run in enumerate(runs):
            # ID
            id_item = QTableWidgetItem(str(run.id))
            id_item.setData(Qt.ItemDataRole.UserRole, run.id)
            self.table.setItem(row, 0, id_item)

            # Device
            device_item = QTableWidgetItem(run.device_id)
            self.table.setItem(row, 1, device_item)

            # Package
            package_item = QTableWidgetItem(run.app_package)
            self.table.setItem(row, 2, package_item)

            # Start Time
            start_time = run.start_time.strftime("%Y-%m-%d %H:%M:%S")
            start_time_item = QTableWidgetItem(start_time)
            self.table.setItem(row, 3, start_time_item)

            # End Time
            if run.end_time:
                end_time = run.end_time.strftime("%Y-%m-%d %H:%M:%S")
            else:
                end_time = "N/A"
            end_time_item = QTableWidgetItem(end_time)
            self.table.setItem(row, 4, end_time_item)

            # Status
            status_item = QTableWidgetItem(run.status)
            # Color code status
            if run.status == "RUNNING":
                status_item.setForeground(QColor("#0066CC"))  # Blue
            elif run.status == "STOPPED":
                status_item.setForeground(QColor("#009900"))  # Green
            elif run.status == "COMPLETED":
                status_item.setForeground(QColor("#009900"))  # Green
            elif run.status == "ERROR":
                status_item.setForeground(QColor("#CC0000"))  # Red
            elif run.status == "INTERRUPTED":
                status_item.setForeground(QColor("#DAA520"))  # Goldenrod/Orange
            self.table.setItem(row, 5, status_item)

            # Steps
            steps_item = QTableWidgetItem(str(run.total_steps))
            self.table.setItem(row, 6, steps_item)

            # Screens
            screens_item = QTableWidgetItem(str(run.unique_screens))
            self.table.setItem(row, 7, screens_item)

            # Model
            model_text = ""
            if run.ai_provider and run.ai_model:
                model_text = f"{run.ai_provider}/{run.ai_model}"
            model_item = QTableWidgetItem(model_text)
            self.table.setItem(row, 8, model_item)

            # Action Button (Open Folder)
            # Only enable if folder exists
            session_path = session_manager.get_session_path(run)

            open_btn = QPushButton("📂 Open")
            open_btn.setToolTip("Open Run Folder")
            if session_path:
                open_btn.clicked.connect(lambda checked=False, path=session_path: self._open_folder(path))
            else:
                open_btn.setEnabled(False)
                open_btn.setToolTip("Folder not found")

            self.table.setCellWidget(row, 9, open_btn)

        # Restore selection
        if selected_id is not None:
             for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == selected_id:
                    self.table.selectRow(row)
                    break

    def _open_folder(self, path: str):
        """Open folder in system file explorer."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open folder: {e}")

    def _on_selection_changed(self):
        """Handle table selection change."""
        selected_items = self.table.selectedItems()
        has_selection = len(selected_items) > 0

        self.delete_button.setEnabled(has_selection)
        self.report_button.setEnabled(has_selection)
        self.mobsf_button.setEnabled(has_selection)
        self._update_stats_button_state()

    def _update_stats_button_state(self):
        """Enable the View Stats button only when stats exist for the selection."""
        if not self._run_stats_repository:
            self.stats_button.setEnabled(False)
            self.stats_button.setToolTip("Detailed statistics are not available")
            return

        run_id = self.get_selected_run_id()
        if run_id is None:
            self.stats_button.setEnabled(False)
            self.stats_button.setToolTip("Select a run to view its detailed statistics")
            return

        try:
            has_stats = self._run_stats_repository.get_run_stats(run_id) is not None
        except Exception:
            has_stats = False

        self.stats_button.setEnabled(has_stats)
        if has_stats:
            self.stats_button.setToolTip("View detailed persisted statistics for the selected run")
        else:
            self.stats_button.setToolTip(
                "No persisted statistics for this run (stats are saved when a crawl completes)"
            )

    def _on_view_stats_clicked(self):
        """Open the run_stats detail dialog for the selected run."""
        if not self._run_stats_repository:
            return
        run_id = self.get_selected_run_id()
        if run_id is None:
            return
        stats = self._run_stats_repository.get_run_stats(run_id)
        if stats is None:
            QMessageBox.information(
                self,
                "Run Stats",
                f"No persisted statistics found for run {run_id}.\n\n"
                "Stats are saved when a crawl completes. Older runs (created before "
                "this feature) will not have a record.",
            )
            return

        dialog = RunStatsDialog(stats, parent=self)
        dialog.exec()

    def _on_delete_clicked(self):
        """Handle delete button click."""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        run_id_item = self.table.item(row, 0)
        if run_id_item is None:
            return

        run_id = run_id_item.data(Qt.ItemDataRole.UserRole)

        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete run {run_id}?\n\n"
            "This will delete the run record and all related data from the database.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                deleted = self._run_repository.delete_run(run_id)
                if deleted:
                    # Remove row from table
                    self.table.removeRow(row)
                    self.run_deleted.emit(run_id)
                    QMessageBox.information(
                        self,
                        "Run Deleted",
                        f"Run {run_id} has been deleted successfully."
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Delete Failed",
                        f"Failed to delete run {run_id}."
                    )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete run {run_id}: {e}"
                )

    def _on_generate_report_clicked(self):
        """Handle generate report button click."""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        run_id_item = self.table.item(row, 0)
        if run_id_item is None:
            return

        run_id = run_id_item.data(Qt.ItemDataRole.UserRole)

        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Generate Report",
            f"Generate enhanced report for run {run_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                report_path = self._report_generator.generate(run_id)
                self.report_generated.emit(run_id)
                QMessageBox.information(
                    self,
                    "Report Generated",
                    f"Report generated successfully:\n{report_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to generate report: {e}"
                )

    def _on_mobsf_clicked(self):
        """Handle MobSF button click."""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        run_id_item = self.table.item(row, 0)
        if run_id_item is None:
            return

        run_id = run_id_item.data(Qt.ItemDataRole.UserRole)
        package_item = self.table.item(row, 2)
        if package_item is None:
            return

        package = package_item.text()

        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Run MobSF Analysis",
            f"Run MobSF static analysis for package {package}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                run = self._get_run_by_id(run_id)
                if not run:
                    raise ValueError(f"Run {run_id} not found")

                if not hasattr(self._mobsf_manager, "analyze_run"):
                    self._mobsf_manager.analyze(package)
                    self.mobsf_completed.emit(run_id)
                    QMessageBox.information(
                        self,
                        "MobSF Analysis Complete",
                        f"MobSF analysis completed for {package}.\n"
                        f"Results saved to session folder."
                    )
                    return

                self.mobsf_button.setEnabled(False)
                self.mobsf_button.setText("Running MobSF...")
                worker = MobSFAnalysisWorker(run, self._mobsf_manager)
                worker.analysis_finished.connect(self._on_mobsf_finished)
                worker.analysis_failed.connect(self._on_mobsf_failed)
                worker.finished.connect(worker.deleteLater)
                worker.finished.connect(lambda: setattr(self, "_mobsf_worker", None))
                self._mobsf_worker = worker
                worker.start()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to run MobSF analysis: {e}"
                )

    def _get_run_by_id(self, run_id: int):
        """Fetch a run from repositories with or without get_run_by_id."""
        if hasattr(self._run_repository, "get_run_by_id"):
            return self._run_repository.get_run_by_id(run_id)
        return next((run for run in self._run_repository.get_all_runs() if run.id == run_id), None)

    def _on_mobsf_finished(self, run_id: int, result):
        """Handle MobSF worker completion."""
        self.mobsf_button.setText("Run MobSF")
        self.mobsf_button.setEnabled(self.get_selected_run_id() is not None)
        self.refresh()

        if result.success:
            self.mobsf_completed.emit(run_id)
            details = []
            if result.scan_id:
                details.append(f"Hash: {result.scan_id}")
            if result.json_path:
                details.append(f"JSON: {result.json_path}")
            if result.report_path:
                details.append(f"PDF: {result.report_path}")
            suffix = "\n" + "\n".join(details) if details else ""
            QMessageBox.information(
                self,
                "MobSF Analysis Complete",
                f"MobSF analysis completed for run {run_id}.{suffix}"
            )
        else:
            QMessageBox.critical(
                self,
                "MobSF Analysis Failed",
                result.error or "MobSF analysis failed with no error message."
            )

    def _on_mobsf_failed(self, run_id: int, error: str):
        """Handle unexpected MobSF worker exceptions."""
        self.mobsf_button.setText("Run MobSF")
        self.mobsf_button.setEnabled(self.get_selected_run_id() is not None)
        self.refresh()
        QMessageBox.critical(
            self,
            "MobSF Analysis Failed",
            error or f"MobSF analysis failed for run {run_id}."
        )

    def refresh(self):
        """Refresh the run history table."""
        self._load_runs()

    def get_selected_run_id(self) -> int | None:
        """Get the ID of the currently selected run.

        Returns:
            Run ID if a run is selected, None otherwise
        """
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return None

        row = selected_rows[0].row()
        run_id_item = self.table.item(row, 0)
        if run_id_item is None:
            return None

        return run_id_item.data(Qt.ItemDataRole.UserRole)
