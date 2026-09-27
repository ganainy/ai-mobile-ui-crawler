"""Repository for the one cached MobSF scan kept per (app_package, APK build)."""

import logging
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime

from mobile_crawler.infrastructure.database import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class MobSFScanRecord:
    """One completed MobSF scan, keyed by the exact APK bytes that produced it."""

    app_package: str
    apk_sha256: str
    file_hash: str | None
    run_id: int | None
    pdf_report_path: str | None
    json_report_path: str | None
    scorecard_json: str | None
    scanned_at: datetime
    app_version_key: str | None = None
    id: int | None = None


class MobSFScanRepository:
    """Looks up and records cached MobSF results so a package is only ever scanned once per build."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def find_by_version(self, app_package: str, app_version_key: str) -> MobSFScanRecord | None:
        """Return the most recent scan recorded for this package's version, or None."""
        with closing(self.db_manager.get_connection()) as conn:
            cursor = conn.execute(
                "SELECT * FROM mobsf_scans WHERE app_package = ? AND app_version_key = ? "
                "ORDER BY scanned_at DESC LIMIT 1",
                (app_package, app_version_key),
            )
            row = cursor.fetchone()
            return self._row_to_record(row) if row else None

    def find_by_hash(self, app_package: str, apk_sha256: str) -> MobSFScanRecord | None:
        """Return the scan recorded for this exact APK content, or None."""
        with closing(self.db_manager.get_connection()) as conn:
            cursor = conn.execute(
                "SELECT * FROM mobsf_scans WHERE app_package = ? AND apk_sha256 = ?",
                (app_package, apk_sha256),
            )
            row = cursor.fetchone()
            return self._row_to_record(row) if row else None

    def upsert(self, record: MobSFScanRecord) -> int:
        """Insert or replace the cached scan for (app_package, apk_sha256)."""
        with closing(self.db_manager.get_connection()) as conn:
            cursor = conn.execute(
                """
                INSERT INTO mobsf_scans (
                    app_package, app_version_key, apk_sha256, file_hash, run_id,
                    pdf_report_path, json_report_path, scorecard_json, scanned_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(app_package, apk_sha256) DO UPDATE SET
                    app_version_key = excluded.app_version_key,
                    file_hash = excluded.file_hash,
                    run_id = excluded.run_id,
                    pdf_report_path = excluded.pdf_report_path,
                    json_report_path = excluded.json_report_path,
                    scorecard_json = excluded.scorecard_json,
                    scanned_at = excluded.scanned_at
                """,
                (
                    record.app_package,
                    record.app_version_key,
                    record.apk_sha256,
                    record.file_hash,
                    record.run_id,
                    record.pdf_report_path,
                    record.json_report_path,
                    record.scorecard_json,
                    record.scanned_at.isoformat(),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def _row_to_record(self, row: sqlite3.Row) -> MobSFScanRecord:
        return MobSFScanRecord(
            id=row["id"],
            app_package=row["app_package"],
            app_version_key=row["app_version_key"],
            apk_sha256=row["apk_sha256"],
            file_hash=row["file_hash"],
            run_id=row["run_id"],
            pdf_report_path=row["pdf_report_path"],
            json_report_path=row["json_report_path"],
            scorecard_json=row["scorecard_json"],
            scanned_at=datetime.fromisoformat(row["scanned_at"]),
        )
