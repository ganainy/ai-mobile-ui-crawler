"""RunFolderLayout: where each file of a run folder lives."""

import os
import time

from mobile_crawler.domain.run_folder_layout import RunFolderLayout


def test_every_report_lives_under_reports(tmp_path):
    layout = RunFolderLayout(tmp_path)

    reports = tmp_path / "reports"
    assert layout.reports_dir == reports
    assert layout.run_report_html == reports / "run_report.html"
    assert layout.analysis_dir == reports / "analysis"
    assert layout.mobsf_dir == reports / "mobsf"
    assert layout.config_snapshot == reports / "config_snapshot.json"
    assert layout.crawler_trace == reports / "crawler_trace.jsonl"


def test_raw_artifact_folders_stay_at_the_root(tmp_path):
    layout = RunFolderLayout(str(tmp_path))

    assert layout.screenshots_dir == tmp_path / "screenshots"
    assert layout.pcap_dir == tmp_path / "pcap"
    assert layout.videos_dir == tmp_path / "videos"
    assert layout.apks_dir == tmp_path / "apks"


def test_created_folders_have_no_logs_or_data(tmp_path):
    assert set(RunFolderLayout.CREATED_SUBFOLDERS) == {"screenshots", "reports", "pcap", "videos", "apks"}


def test_mobsf_json_report_is_none_when_absent(tmp_path):
    assert RunFolderLayout(tmp_path).find_mobsf_json_report() is None


def test_mobsf_json_report_picks_newest(tmp_path):
    layout = RunFolderLayout(tmp_path)
    layout.mobsf_dir.mkdir(parents=True)
    old = layout.mobsf_dir / "aaa_report.json"
    new = layout.mobsf_dir / "bbb_report.json"
    old.write_text("{}")
    new.write_text("{}")
    past = time.time() - 100
    os.utime(old, (past, past))

    assert layout.find_mobsf_json_report() == new


def test_pcap_is_none_when_absent(tmp_path):
    assert RunFolderLayout(tmp_path).find_pcap() is None


def test_pcap_picks_newest_capture(tmp_path):
    layout = RunFolderLayout(tmp_path)
    layout.pcap_dir.mkdir()
    old = layout.pcap_dir / "com.app_run1_a.pcap"
    new = layout.pcap_dir / "com.app_run1_b.pcap"
    old.write_bytes(b"x")
    new.write_bytes(b"x")
    past = time.time() - 100
    os.utime(old, (past, past))

    assert layout.find_pcap() == new
