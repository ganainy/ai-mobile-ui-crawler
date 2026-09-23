import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from mobile_crawler.domain.report_generator import ReportGenerator
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import Run, RunRepository
from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager


class TestExportConsolidation:
    @pytest.fixture
    def temp_dir(self):
        dir_path = tempfile.mkdtemp()
        yield dir_path
        shutil.rmtree(dir_path, ignore_errors=True)

    @pytest.fixture
    def db_manager(self, temp_dir):
        db_path = Path(temp_dir) / "test_crawler.db"
        db = DatabaseManager(db_path=db_path)
        db.create_schema()
        yield db
        db.close()

    @pytest.fixture
    def session_manager(self, temp_dir):
        return SessionFolderManager(base_path=os.path.join(temp_dir, "output_data"))

    def test_report_saves_bundle_to_session_reports_analysis_folder(self, db_manager, session_manager, temp_dir):
        run_repo = RunRepository(db_manager)

        # 1. Create run with session path
        session_root = os.path.join(temp_dir, "output_data", "run_1")
        os.makedirs(session_root, exist_ok=True)

        run_id = run_repo.create_run(
            Run(
                id=1,
                device_id="test_device",
                app_package="com.test",
                start_activity=None,
                start_time=datetime.now(),
                end_time=None,
                status="COMPLETED",
                ai_provider="gemini",
                ai_model="pro",
                session_path=os.path.abspath(session_root),
            )
        )

        # 2. Generate the Run Report (HTML + Analysis Bundle)
        ReportGenerator(db_manager).generate(run_id)

        # 3. Verify the bundle is written inside the session folder
        analysis_dir = Path(os.path.abspath(session_root)) / "reports" / "analysis"
        assert (analysis_dir / "run.json").exists()
