import os
import shutil
import tempfile
from pathlib import Path
import pytest
from datetime import datetime

from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import RunRepository, Run
from mobile_crawler.infrastructure.run_exporter import RunExporter
from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager

class TestExportConsolidation:
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

    def test_export_saves_to_session_data_folder(self, db_manager, session_manager, temp_dir):
        run_repo = RunRepository(db_manager)
        
        # 1. Create run with session path
        session_root = os.path.join(temp_dir, "output_data", "run_1")
        os.makedirs(os.path.join(session_root, "data"), exist_ok=True)
        
        run_id = run_repo.create_run(Run(
            id=1,
            device_id="test_device",
            app_package="com.test",
            start_activity=None,
            start_time=datetime.now(),
            end_time=None,
            status="COMPLETED",
            ai_provider="gemini",
            ai_model="pro",
            session_path=os.path.abspath(session_root)
        ))
        
        # 2. Export run
        exporter = RunExporter(db_manager)
        export_path = exporter.export_run(run_id)
        
        # 3. Verify path
        expected_dir = os.path.abspath(os.path.join(session_root, "data"))
        assert str(Path(export_path).parent) == expected_dir
        assert os.path.exists(export_path)
        assert export_path.name.endswith(".json")
