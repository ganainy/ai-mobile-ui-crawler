"""Tests for MobSFScanRepository, the per-package MobSF scan cache."""

from datetime import datetime

from mobile_crawler.infrastructure.database import DatabaseManager
from mobile_crawler.infrastructure.mobsf_scan_repository import MobSFScanRecord, MobSFScanRepository


def _make_repo(tmp_path) -> MobSFScanRepository:
    db_manager = DatabaseManager(db_path=tmp_path / "crawler.db")
    db_manager.create_schema()
    # mobsf_scans.run_id is a real FK into runs(id); seed a few rows for the tests to reference.
    conn = db_manager.get_connection()
    for run_id in (1, 2, 5):
        conn.execute(
            "INSERT INTO runs (id, device_id, app_package, start_time, status) VALUES (?, 'dev', 'pkg', 'now', 'DONE')",
            (run_id,),
        )
    conn.commit()
    conn.close()
    return MobSFScanRepository(db_manager)


def _record(**overrides) -> MobSFScanRecord:
    defaults = dict(
        app_package="com.example.app",
        app_version_key="1.0:1",
        apk_sha256="abc123",
        file_hash="h1",
        run_id=1,
        pdf_report_path="/reports/h1.pdf",
        json_report_path="/reports/h1.json",
        scorecard_json='{"score": 90}',
        scanned_at=datetime(2026, 1, 1, 12, 0, 0),
    )
    defaults.update(overrides)
    return MobSFScanRecord(**defaults)


class TestMobSFScanRepository:
    def test_find_by_hash_returns_none_when_missing(self, tmp_path):
        repo = _make_repo(tmp_path)
        assert repo.find_by_hash("com.example.app", "nope") is None

    def test_find_by_version_returns_none_when_missing(self, tmp_path):
        repo = _make_repo(tmp_path)
        assert repo.find_by_version("com.example.app", "1.0:1") is None

    def test_upsert_then_find_by_hash_and_version(self, tmp_path):
        repo = _make_repo(tmp_path)
        repo.upsert(_record())

        by_hash = repo.find_by_hash("com.example.app", "abc123")
        by_version = repo.find_by_version("com.example.app", "1.0:1")

        assert by_hash is not None
        assert by_hash.file_hash == "h1"
        assert by_hash.run_id == 1
        assert by_version is not None
        assert by_version.apk_sha256 == "abc123"

    def test_upsert_replaces_existing_record_for_same_package_and_hash(self, tmp_path):
        repo = _make_repo(tmp_path)
        repo.upsert(_record())
        repo.upsert(_record(run_id=2, file_hash="h2", scanned_at=datetime(2026, 2, 1, 0, 0, 0)))

        record = repo.find_by_hash("com.example.app", "abc123")

        assert record.run_id == 2
        assert record.file_hash == "h2"

    def test_different_packages_with_same_hash_are_independent(self, tmp_path):
        repo = _make_repo(tmp_path)
        repo.upsert(_record(app_package="com.example.app"))
        repo.upsert(_record(app_package="com.other.app", run_id=5))

        assert repo.find_by_hash("com.example.app", "abc123").run_id == 1
        assert repo.find_by_hash("com.other.app", "abc123").run_id == 5

    def test_find_by_version_returns_most_recent_when_several_hashes_share_a_version(self, tmp_path):
        repo = _make_repo(tmp_path)
        repo.upsert(_record(apk_sha256="old", scanned_at=datetime(2026, 1, 1)))
        repo.upsert(_record(apk_sha256="new", scanned_at=datetime(2026, 1, 2)))

        record = repo.find_by_version("com.example.app", "1.0:1")

        assert record.apk_sha256 == "new"
