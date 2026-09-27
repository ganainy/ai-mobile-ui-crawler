---
author: claude
updated: 2026-09-27
---
# Automatic SNI extraction after PCAP capture

Continuing from [emulator-tls-ca-naming](2026-09-27-emulator-tls-ca-naming.md): while diagnosing why decryption wasn't happening, the user asked for a way to pull SNI hostnames out of a pcap without Wireshark. That became a standalone script (`scripts/extract_sni.py`), first tried with `scapy` (installed then uninstalled once we noticed `dpkt` was already a project dependency), then fixed for two real bugs found while testing against actual run captures:

1. PCAPdroid's pcap uses linktype 101 (Linux/Android raw-IP VPN capture), not `dpkt.pcap.DLT_RAW` (12, the BSD variant) — every packet was silently skipped until both were accepted.
2. A ClientHello's SNI extension can be split across TCP segments; a single-packet parser truncates the hostname (`fitness.googleapis.com` → `fitne` in run 196). Fixed with per-flow TCP reassembly (buffer segments by seq number once a flow's first payload byte is `0x16`, concatenate contiguous runs, only accept a parsed SNI once the buffer is complete).

## What changed

The user then asked to make this automatic: a checkbox in the PCAP settings, on by default in GUI and CLI, writing the SNI list next to the pcap file whenever a capture is pulled.

- `src/mobile_crawler/infrastructure/sni_extractor.py`: the reassembly/parsing logic moved here from the script (`extract_sni_records`, `write_sni_report`). `scripts/extract_sni.py` is now a thin CLI wrapper over it.
- `src/mobile_crawler/domain/traffic_capture_manager.py`: `stop_capture_and_pull_async` calls `_extract_sni_report` right after a successful pull (file exists, size > 0), gated by `config_manager.get("pcap_extract_sni", True)`. Extraction failure is caught and logged (`logger.warning(..., exc_info=True)`), never fails the pull.
- `src/mobile_crawler/config/defaults.py`: new `pcap_extract_sni: True`. No CLI flag added — same as `pcapdroid_tls_decryption`, it's just a config default both GUI and CLI read.
- `src/mobile_crawler/ui/widgets/settings_panel.py`: new "Extract SNI hostnames after capture" checkbox in Settings > Integrations > Traffic Capture (PCAPdroid), checked by default, enabled/disabled together with "Enable Traffic Capture" (same pattern as the API key field).

## Verification

Ran `scripts/extract_sni.py` against all four real pcaps under the user's actual `output_data` folder (runs 195 Headspace, 196 Google Fit, 198 and 201 Whisk) before and after the reassembly fix — confirmed the `fitne` truncation in run 196 became the correct `fitness.googleapis.com`, and run 201's output matched what `docs/STATE.md` had already recorded independently (`www.gstatic.com`, `aisandbox-pa.googleapis.com`).

Added `tests/infrastructure/test_sni_extractor.py` (single-packet, fragmented reassembly using a synthetic pcap built with `dpkt.pcap.Writer`, no-TLS-traffic, and the report file) and two tests in `tests/domain/test_traffic_capture_manager.py` (extraction called after a successful pull, skipped when `pcap_extract_sni` is False). Full suite green except two pre-existing failures in `tests/ui/test_main_window.py` (`stats_dashboard` AttributeError) confirmed present on `main` before this session via `git stash`.

Not tried against a real device crawl — only against already-saved pcap files.

## Issue #31 updated

Posted a [comment](https://github.com/ganainy/ai-mobile-ui-crawler/issues/31#issuecomment-5855899579) with these findings plus two more from the live PCAPdroid debugging session that preceded this work:

- The "PCAPdroid CA" trust-store naming correction (see [emulator-tls-ca-naming](2026-09-27-emulator-tls-ca-naming.md)) was a false alarm, not a misconfiguration.
- Root cause of "decryption isn't even attempted" on the user's live capture: PCAPdroid's **Block QUIC** was at its default "Never", so almost all Google-domain traffic went out as QUIC/UDP and never reached the mitm add-on's TCP interception at all — this directly confirms the issue's own task item 4. Fix is a settings toggle + fresh capture, not a code change.
- Flagged still-open items on the issue: Flow's ABI install failure on the emulator, the Block-QUIC fix hasn't been re-verified against a real decryption test yet, and per-host byte aggregation (vs. just hostname listing) for the "Analysis step" task isn't built.
