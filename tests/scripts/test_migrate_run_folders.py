"""scripts/migrate_run_folders.py moves old run folders to the reports/ layout."""

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "migrate_run_folders.py"
_spec = importlib.util.spec_from_file_location("migrate_run_folders", _SCRIPT)
migrate = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = migrate  # dataclasses look their module up here
_spec.loader.exec_module(migrate)

HASH = "0123456789abcdef0123456789abcdef"


def _write(path: Path, text: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def old_run(tmp_path):
    """A run folder in the pre-#26 layout, with every kind of report."""
    run = tmp_path / "output_data" / "run_180_20260923_101500"
    _write(run / "screenshots" / "step_1.png", "png")
    _write(run / "pcap" / "app_run180_20260923.pcap")
    _write(run / "videos" / "manifest.json", "{}")
    _write(run / "apks" / "com.app.apk")
    _write(run / "reports" / "report_run_180.html", '<img src="../screenshots/step_1.png">')
    _write(run / "reports" / "report_run_180.json", "{}")
    _write(run / "reports" / f"{HASH}_report.json", "{}")
    _write(run / "reports" / f"{HASH}_report.pdf", "pdf")
    _write(run / "analysis" / "analysis.md", "# md")
    _write(run / "analysis" / "steps.jsonl", '{"screenshot": "screenshots/step_1.png"}')
    _write(run / "analysis" / "run.json", "{}")
    _write(run / "data" / "config_snapshot.json", "{}")
    _write(run / "logs" / "crawler_trace.jsonl", "{}")
    return run


def _tree(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def test_migrates_every_report_into_reports(old_run):
    migrate.migrate_run_folder(old_run)

    assert _tree(old_run) == {
        "screenshots/step_1.png",
        "pcap/app_run180_20260923.pcap",
        "videos/manifest.json",
        "apks/com.app.apk",
        "reports/run_report.html",
        f"reports/mobsf/{HASH}_report.json",
        f"reports/mobsf/{HASH}_report.pdf",
        "reports/analysis/analysis.md",
        "reports/analysis/steps.jsonl",
        "reports/analysis/run.json",
        "reports/config_snapshot.json",
        "reports/crawler_trace.jsonl",
    }
    for gone in ("analysis", "data", "logs"):
        assert not (old_run / gone).exists()


def test_screenshot_links_still_resolve_after_migration(old_run):
    migrate.migrate_run_folder(old_run)

    html = old_run / "reports" / "run_report.html"
    assert (html.parent / "../screenshots/step_1.png").resolve().is_file()
    # steps.jsonl paths are relative to the run folder, which did not move
    assert (old_run / "screenshots/step_1.png").is_file()


def test_second_run_changes_nothing(old_run):
    migrate.migrate_run_folder(old_run)
    before = _tree(old_run)

    assert migrate.migrate_run_folder(old_run) == []
    assert _tree(old_run) == before


def test_dry_run_reports_but_touches_nothing(old_run):
    before = _tree(old_run)

    actions = migrate.migrate_run_folder(old_run, dry_run=True)

    assert _tree(old_run) == before
    described = "\n".join(str(a) for a in actions)
    assert "report_run_180.html" in described
    assert "delete" in described and "report_run_180.json" in described


def test_old_droidrun_trace_and_legacy_export_move_into_reports(tmp_path):
    run = tmp_path / "run_7_20260405_014238"
    _write(run / "logs" / "droidrun_trace.jsonl")
    _write(run / "data" / "run_7_2026-04-05_014238.json")

    migrate.migrate_run_folder(run)

    assert _tree(run) == {"reports/crawler_trace.jsonl", "reports/run_7_2026-04-05_014238.json"}


def test_never_overwrites_an_existing_target(tmp_path):
    run = tmp_path / "run_5_x"
    _write(run / "data" / "config_snapshot.json", "old")
    _write(run / "reports" / "config_snapshot.json", "new")

    actions = migrate.migrate_run_folder(run)

    assert (run / "reports" / "config_snapshot.json").read_text(encoding="utf-8") == "new"
    assert (run / "data" / "config_snapshot.json").read_text(encoding="utf-8") == "old"
    assert any("skip" in str(a) for a in actions)


def test_empty_legacy_folders_are_removed(tmp_path):
    run = tmp_path / "run_3_x"
    (run / "logs").mkdir(parents=True)
    (run / "data").mkdir()

    migrate.migrate_run_folder(run)

    assert not (run / "logs").exists()
    assert not (run / "data").exists()


def test_migrate_all_only_touches_run_folders(tmp_path, old_run):
    base = old_run.parent
    other = _write(base / "notes" / "logs" / "keep.txt")

    results = migrate.migrate_all(base)

    assert list(results) == [old_run]
    assert other.is_file()
    assert (old_run / "reports" / "run_report.html").is_file()
