---
author: claude
updated: 2026-09-27
---
# Run History: artifact presence columns

User asked (from a screenshot of the Run History table) to show, per run, whether the packet capture (+SNI extraction), MobSF analysis, telemetry tracing, UI parser mode, video recording and run report exist.

## What changed

`src/mobile_crawler/ui/widgets/run_history_view.py`: table grew from 10 to 16 columns. New columns sit between **Model** and **Actions**:

- **PCAP+SNI** — `RunFolderLayout.find_pcap()`; shows `✓ +SNI` when the pcap's `.sni.txt` sidecar also exists (written by `infrastructure/sni_extractor.py`), else plain `✓`, else `—`.
- **MobSF** — `RunFolderLayout.find_mobsf_json_report()` exists.
- **Tracing** — `run.trace_id` is set (Phoenix/Langfuse telemetry session id, written by `crawler_loop.py` when `enable_tracing` was on).
- **UI Parser** — the actual `ui_parser_mode` value from `reports/config_snapshot.json` (`read_config_snapshot`), not a boolean — more useful than yes/no since the mode itself (e.g. `omniparser` vs accessibility) is the interesting fact.
- **Video** — any `videos/*.mp4`.
- **Report** — `reports/run_report.html` exists.

All reuse existing lookups (`RunFolderLayout`, `read_config_snapshot`) already used by `report_generator.py`; no new file formats or scan logic. A shared `_artifact_item()` helper colors `✓` green / `—` gray.

## Testing

`tests/ui/test_run_history_view.py` updated for the new column count/headers/index shift (Actions moved from column 9 to 15); added a test asserting all-dash state for a run with no session folder on disk. Full file green (33 tests). Not exercised in the real GUI — only Qt widget tests.

Two pre-existing failures in `tests/ui/test_main_window.py` (`stats_dashboard` `AttributeError`) are unrelated, from other in-progress work already on this branch.
