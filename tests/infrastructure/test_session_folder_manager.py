import os
import pytest
from mobile_crawler.infrastructure.session_folder_manager import SessionFolderManager


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