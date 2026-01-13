import os
from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.run_repository import RunRepository, Run
from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager
from datetime import datetime

def validate():
    db = DatabaseManager()
    db.create_schema()
    run_repo = RunRepository(db)
    session_mgr = SessionFolderManager()

    # Create run
    run_id = run_repo.create_run(Run(
        id=None,
        device_id="test_device",
        app_package="com.test",
        start_activity=None,
        start_time=datetime.now(),
        end_time=None,
        status="RUNNING",
        ai_provider="gemini",
        ai_model="pro"
    ))

    # Simulate start of run
    session_path = session_mgr.create_session_folder(run_id)
    run_repo.update_session_path(run_id, session_path)

    print(f"Session path created: {session_path}")
    print(f"Screenshots folder exists: {os.path.exists(os.path.join(session_path, 'screenshots'))}")
    print(f"Reports folder exists: {os.path.exists(os.path.join(session_path, 'reports'))}")
    print(f"Data folder exists: {os.path.exists(os.path.join(session_path, 'data'))}")
    
    # Verify DB entry
    run = run_repo.get_run(run_id)
    print(f"DB session_path: {run.session_path}")
    assert run.session_path == session_path

if __name__ == "__main__":
    validate()
