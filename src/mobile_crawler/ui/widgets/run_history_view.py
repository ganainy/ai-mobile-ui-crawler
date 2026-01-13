"""Run history view widget for mobile-crawler GUI."""

from typing import TYPE_CHECKING
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QCheckBox,
    QDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

if TYPE_CHECKING:
    from mobile_crawler.infrastructure.run_repository import RunRepository
    from mobile_crawler.domain.report_generator import ReportGenerator
    from mobile_crawler.infrastructure.mobsf_manager import MobSFManager


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
        parent=None
    ):
        """Initialize run history view widget.
        
        Args:
            run_repository: RunRepository instance for fetching runs
            report_generator: ReportGenerator instance for generating reports
            mobsf_manager: MobSFManager instance for running MobSF analysis
            parent: Parent widget
        """
        super().__init__(parent)
        self._run_repository = run_repository
        self._report_generator = report_generator
        self._mobsf_manager = mobsf_manager
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
        self.refresh_button.clicked.connect(self._load_runs)
        buttons_layout.addWidget(self.refresh_button)

        # Delete button
        self.delete_button = QPushButton("Delete Run")
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.delete_button.setEnabled(False)
        buttons_layout.addWidget(self.delete_button)

        # Generate Report button
        self.report_button = QPushButton("Generate Report")
        self.report_button.clicked.connect(self._on_generate_report_clicked)
        self.report_button.setEnabled(False)
        buttons_layout.addWidget(self.report_button)

        # Run MobSF button
        self.mobsf_button = QPushButton("Run MobSF")
        self.mobsf_button.clicked.connect(self._on_mobsf_clicked)
        self.mobsf_button.setEnabled(False)
        buttons_layout.addWidget(self.mobsf_button)

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
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        
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
            f"Generate PDF report for run {run_id}?",
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
                run = self._run_repository.get_run(run_id)
                if not run:
                    raise ValueError(f"Run {run_id} not found")
                
                self._mobsf_manager.analyze_run(run, run.device_id)
                self.mobsf_completed.emit(run_id)
                QMessageBox.information(
                    self,
                    "MobSF Analysis Complete",
                    f"MobSF analysis completed for {package}.\n"
                    f"Results saved to session folder."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to run MobSF analysis: {e}"
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
