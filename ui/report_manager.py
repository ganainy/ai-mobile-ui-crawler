# ui/report_manager.py - Handles PDF report generation

import logging
import sqlite3
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import QApplication

class ReportManager:
    """Handles PDF report generation for crawl runs."""
    
    def __init__(self, config, log_callback, busy_callback):
        self.config = config
        self.log_callback = log_callback
        self.busy_callback = busy_callback
        
    def generate_report(self):
        """Generate a PDF report for the latest crawl run."""
        try:
            from domain.analysis_viewer import XHTML2PDF_AVAILABLE, RunAnalyzer
        except Exception:
            self.log_callback("Error: PDF analysis not available.", "red")
            return False

        app_package = self.config.get("APP_PACKAGE", None)
        output_data_dir = self.config.get("OUTPUT_DATA_DIR", None)
        session_dir_str = getattr(self.config, 'SESSION_DIR', None)
        db_path_str = self.config.get("DB_NAME", None)

        if not app_package:
            self.log_callback("Error: No target app selected.", "red")
            return False
        if not output_data_dir:
            self.log_callback("Error: OUTPUT_DATA_DIR is not configured.", "red")
            return False

        resolved_db_path, resolved_session_dir = self._resolve_paths(
            db_path_str, session_dir_str, output_data_dir, app_package
        )

        if not resolved_db_path:
            return False

        run_id = self._get_latest_run_id(resolved_db_path)
        if run_id is None:
            return False

        # Prepare output
        reports_dir_str = self.config.get("PDF_REPORT_DIR", "")
        if reports_dir_str and "{session_dir}" in reports_dir_str:
            reports_dir_str = reports_dir_str.replace("{session_dir}", str(resolved_session_dir))
            
        if reports_dir_str:
             reports_dir = Path(reports_dir_str)
        else:
             reports_dir = resolved_session_dir / "reports"
             
        reports_dir.mkdir(parents=True, exist_ok=True)

        pdf_path = str(reports_dir / f"{app_package}_analysis.pdf")

        try:
            self.busy_callback(True, "Generating report...")
            analyzer = RunAnalyzer(
                db_path=str(resolved_db_path),
                output_data_dir=output_data_dir,
                app_package_for_run=app_package,
            )
            result = analyzer.analyze_run_to_pdf(run_id, pdf_path)
            
            if result.get("success", False):
                self.log_callback(f"✅ Report generated: {pdf_path}", "green")
                return True
            else:
                error_msg = result.get("error", "Failed to generate report.")
                self.log_callback(f"Error: {error_msg}", "red")
                return False
        finally:
            self.busy_callback(False)

    def _resolve_paths(self, db_path_str, session_dir_str, output_data_dir, app_package):
        """Resolve database and session directory paths."""
        if db_path_str and Path(db_path_str).exists():
            resolved_db_path = Path(db_path_str)
            resolved_session_dir = Path(session_dir_str) if session_dir_str else Path(db_path_str).parent.parent
            return resolved_db_path, resolved_session_dir
        
        # Fallback: find latest
        try:
            candidates = []
            output_dir = Path(output_data_dir)
            
            # Check if sessions are in a 'sessions' subdirectory (common structure)
            sessions_dir = output_dir / "sessions"
            if sessions_dir.exists() and sessions_dir.is_dir():
                search_dir = sessions_dir
            else:
                search_dir = output_dir

            # Sanitize app package for matching (dots often replaced by underscores)
            sanitized_package = app_package.replace('.', '_')
            
            for sd in search_dir.iterdir():
                if sd.is_dir() and "_" in sd.name:
                    # Robust matching: check if sanitized package name is in the directory name
                    # strict splitting is brittle due to device IDs and extra underscores
                    if sanitized_package in sd.name:
                        candidates.append(sd)
            
            if not candidates:
                self.log_callback(f"Error: No session directories found for app '{app_package}' in {search_dir}.", "red")
                return None, None
                
            candidates.sort(key=lambda p: p.name, reverse=True)
            resolved_session_dir = candidates[0]
            db_dir = resolved_session_dir / "database"
            # Check for any .db file
            found_dbs = list(db_dir.glob("*.db")) if db_dir.exists() else []
            
            if not found_dbs:
                self.log_callback(f"Error: No database file found in {db_dir}.", "red")
                return None, None
                
            return found_dbs[0], resolved_session_dir
        except Exception as e:
            self.log_callback(f"Error resolving paths: {e}", "red")
            return None, None

    def _get_latest_run_id(self, db_path: Path) -> Optional[int]:
        """Get the latest run_id from the database."""
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT run_id FROM runs ORDER BY run_id DESC LIMIT 1")
            row = cur.fetchone()
            conn.close()
            
            if row and row[0] is not None:
                return int(row[0])
            self.log_callback("Error: No runs found in database.", "red")
            return None
        except Exception as e:
            self.log_callback(f"Error reading run_id: {e}", "red")
            return None
