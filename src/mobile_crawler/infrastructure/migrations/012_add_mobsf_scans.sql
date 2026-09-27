-- Migration: 012_add_mobsf_scans.sql
-- Description: Add mobsf_scans table, caching one MobSF scan per (app_package, apk_sha256)
-- Created: 2026-09-27

CREATE TABLE IF NOT EXISTS mobsf_scans (
    id INTEGER PRIMARY KEY,
    app_package TEXT NOT NULL,
    app_version_key TEXT,
    apk_sha256 TEXT NOT NULL,
    file_hash TEXT,
    run_id INTEGER,
    pdf_report_path TEXT,
    json_report_path TEXT,
    scorecard_json TEXT,
    scanned_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id),
    UNIQUE (app_package, apk_sha256)
);

CREATE INDEX IF NOT EXISTS idx_mobsf_scans_package ON mobsf_scans(app_package);
CREATE INDEX IF NOT EXISTS idx_mobsf_scans_version ON mobsf_scans(app_package, app_version_key);
