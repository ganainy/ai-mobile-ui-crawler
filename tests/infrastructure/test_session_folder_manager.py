import os
import pytest
from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager
from datetime import datetime, timedelta
from unittest.mock import Mock


def test_create_session_folder(tmp_path):
    manager = SessionFolderManager(base_path=str(tmp_path))
    path = manager.create_session_folder("device1", "com.example.app")
    
    assert os.path.exists(path)
    assert os.path.isdir(path)
    
    # Check subdirectories
    expected_subdirs = ["screenshots", "logs", "video", "data"]
    for subdir in expected_subdirs:
        assert os.path.exists(os.path.join(path, subdir))
        assert os.path.isdir(os.path.join(path, subdir))
    
    # Check folder name format (device_id_app_package_timestamp)
    folder_name = os.path.basename(path)
    parts = folder_name.split("_")
    assert len(parts) == 6  # device1_com.example.app_dd_mm_hh_mm
    assert parts[0] == "device1"
    assert parts[1] == "com.example.app"
    # timestamp parts should be numeric
    assert parts[2].isdigit() and len(parts[2]) == 2  # dd
    assert parts[3].isdigit() and len(parts[3]) == 2  # mm
    assert parts[4].isdigit() and len(parts[4]) == 2  # hh
    assert parts[5].isdigit() and len(parts[5]) == 2  # mm


def test_delete_session_folder(tmp_path):
    manager = SessionFolderManager(base_path=str(tmp_path))
    path = manager.create_session_folder("device1", "com.example.app")
    
    assert os.path.exists(path)
    
    manager.delete_session_folder(path)
    
    assert not os.path.exists(path)


def test_get_session_path(tmp_path):
    manager = SessionFolderManager(base_path=str(tmp_path))
    
    # Setup: Create some session folders manually
    # Current time rounded to minutes
    now = datetime.now().replace(second=0, microsecond=0)
    
    # Folder 1: device1_pkg1_TIME (MATCH)
    ts1 = now.strftime("%d_%m_%H_%M")
    name1 = f"device1_pkg1_{ts1}"
    path1 = tmp_path / name1
    path1.mkdir()
    
    # Folder 2: device1_pkg1_OLDTIME (NO MATCH - 10 mins ago)
    old = now - timedelta(minutes=10)
    ts2 = old.strftime("%d_%m_%H_%M")
    name2 = f"device1_pkg1_{ts2}"
    path2 = tmp_path / name2
    path2.mkdir()
    
    # Folder 3: device2_pkg1_TIME (NO MATCH - diff device)
    name3 = f"device2_pkg1_{ts1}"
    path3 = tmp_path / name3
    path3.mkdir()
    
    # Test 1: Successful match
    run1 = Mock()
    run1.device_id = "device1"
    run1.app_package = "pkg1"
    run1.start_time = now
    
    result = manager.get_session_path(run1)
    # The manager returns absolute path string
    assert result == str(path1.absolute())
    
    # Test 2: Close match (Run time is 2 mins ahead of folder time)
    # Folder created at T, Run time is T+2m
    run2 = Mock()
    run2.device_id = "device1"
    run2.app_package = "pkg1"
    run2.start_time = now + timedelta(minutes=2)
    
    # Should still match path1 as it is within 5 minutes (diff=2)
    result = manager.get_session_path(run2)
    assert result == str(path1.absolute())
    
    # Test 3: No match (Run time is 20 mins ahead)
    run3 = Mock()
    run3.device_id = "device1"
    run3.app_package = "pkg1"
    run3.start_time = now + timedelta(minutes=20)
    
    result = manager.get_session_path(run3)
    assert result is None


def test_get_session_path_run_id_folder(tmp_path, monkeypatch):
    # Setup: Create a mock screenshots directory
    screenshots_dir = tmp_path / "screenshots"
    screenshots_dir.mkdir()
    
    run_id = 99
    run_folder = screenshots_dir / f"run_{run_id}"
    run_folder.mkdir()
    
    # Change working directory to tmp_path during test so os.path.join("screenshots", ...) works
    monkeypatch.chdir(tmp_path)
    
    manager = SessionFolderManager(base_path="non_existent")
    
    run = Mock()
    run.id = run_id
    run.device_id = "device1"
    run.app_package = "pkg1"
    run.start_time = datetime.now()
    
    result = manager.get_session_path(run)
    assert result == str(run_folder.absolute())
