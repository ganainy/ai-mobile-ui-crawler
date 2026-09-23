---
author: claude
date: 2026-09-23
---
# All of a run's reports in `reports/` (issue #26)

New layout, defined once in `domain/run_folder_layout.py` (`RunFolderLayout`):

```text
run_<id>_<date>_<time>/
├── reports/
│   ├── run_report.html        # was reports/report_run_<id>.html
│   ├── analysis/              # was analysis/
│   ├── mobsf/                 # was reports/<hash>_report.json|pdf
│   ├── config_snapshot.json   # was data/config_snapshot.json
│   └── crawler_trace.jsonl    # was logs/crawler_trace.jsonl
├── screenshots/  videos/  pcap/  apks/
```

- Writers: `ReportGenerator` (HTML + bundle paths from the layout; screenshot links relative to the HTML's own folder), `JinjaReportGenerator` no longer writes `report_run_<id>.json`, `MobSFManager` saves into `reports/mobsf/`, `write_config_snapshot`, `configure_run_logging(run_id, log_path, ...)` now takes the trace file path. `SessionFolderManager` no longer creates `logs/` or `data/` (nothing else wrote there).
- Report lookups fixed: the Run Report now finds PCAP (`pcap/*.pcap`, newest) and MobSF (`reports/mobsf/*_report.json`, newest); it looked at `traffic/capture.pcap` and `mobsf/report.json`, which nothing wrote.
- No more working-directory fallbacks: `ReportGenerator.generate` raises `RunFolderMissingError` without a run folder (unless `--output` is given; the bundle then goes next to that HTML; with a run folder `--output` moves only the HTML, as before); `perform_complete_scan` fails with "No run folder ..." instead of writing to `output_data/` in the cwd; `extract_apk_from_device` / `save_*_report` now require their output path. `scan_results_dir` removed. TrafficCaptureManager's `output_data/traffic_captures` fallback left alone (raw artifact, out of scope).
- `scripts/migrate_run_folders.py [--dry-run] [--base PATH]`: moves old run folders to the layout, deletes `report_run_<id>.json`, also moves the older `logs/droidrun_trace.jsonl` (-> `crawler_trace.jsonl`) and legacy `data/run_<id>_<date>.json` exports into `reports/`, removes empty `analysis/`, `data/`, `logs/`. Never overwrites (skips and reports); a second run changes nothing. Screenshot links need no rewriting: the HTML stays in `reports/`, and bundle paths are relative to the run folder.
- Dry run against the real `%APPDATA%\mobile-crawler\output_data`: 179 run folders, 221 moves, 11 deletes, 0 skips. **Not run for real**; the user runs it.
- Docs: README Data Organization + MobSF tree, `docs/cli.md` run-folder table, `report` help text, CONTEXT.md Run Report entry.
- Tests: `test_run_folder_layout.py`, `tests/scripts/test_migrate_run_folders.py`, new ReportGenerator/MobSF/loop assertions. Full suite green. No typechecker in `.venv312`. Not tried on a real crawl.
