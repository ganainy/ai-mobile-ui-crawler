import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from mobile_crawler.domain.report_generator import ReportGenerator
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_exporter import RunExporter
from mobile_crawler.infrastructure.run_repository import Run, RunRepository
from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager


class TestArtifactGrouping:
    @pytest.fixture
    def temp_dir(self):
        dir_path = tempfile.mkdtemp()
        yield dir_path
        shutil.rmtree(dir_path)

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

    def test_full_artifact_flow(self, db_manager, session_manager, temp_dir):
        run_repo = RunRepository(db_manager)

        # 1. Create a run
        run_id = run_repo.create_run(Run(
            id=None,
            device_id="test_device",
            app_package="com.test.app",
            start_activity="MainActivity",
            start_time=datetime.now(),
            end_time=None,
            status="RUNNING",
            ai_provider="test_provider",
            ai_model="test_model"
        ))
        run = run_repo.get_run(run_id)

        # 2. Create session folder
        session_path = session_manager.create_session_folder(run_id)
        run_repo.update_session_path(run_id, session_path)
        run.session_path = session_path

        # Verify folder structure
        assert os.path.exists(session_path)
        assert os.path.exists(os.path.join(session_path, "screenshots"))
        assert os.path.exists(os.path.join(session_path, "reports"))
        assert os.path.exists(os.path.join(session_path, "data"))

        # 3. Test ReportGenerator integration
        rg = ReportGenerator(db_manager)
        report_path = rg.generate(run_id)
        assert "reports" in report_path
        assert os.path.exists(report_path)
        assert Path(report_path).parent.name == "reports"

        # 4. Test RunExporter integration
        exporter = RunExporter(db_manager)
        export_path = exporter.export_run(run_id)
        assert "data" in str(export_path)
        assert os.path.exists(export_path)
        assert Path(export_path).parent.name == "data"
