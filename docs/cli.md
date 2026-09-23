---
author: claude
updated: 2026-09-23
---
# CLI Reference

The CLI is a Click app: `mobile-crawler-cli` (after `pip install -e .`) or `python run_cli.py` from the repo root. Every command has `--help`.

```powershell
mobile-crawler-cli --help
mobile-crawler-cli --version
```

| Command | What it does |
|---|---|
| [`crawl`](#crawl) | Crawl one app, or several apps one after another |
| [`list`](#list) | List runs, connected devices, or apps installed on a device |
| [`stats`](#stats) | Show a finished run's saved statistics |
| [`report`](#report) | (Re)generate a run's HTML report and analysis folder |
| [`mobsf-scan`](#mobsf-scan) | Run MobSF on a finished run's stored APK |
| [`delete`](#delete) | Delete a run and all its data |
| [`scenarios`](#scenarios) | Manage an app's Guided Scenarios |
| [`portal`](#portal) | Check, enable or install Mobilerun Portal on a device |
| [`config`](#config) | Read and write persisted settings and API keys |

Settings and the database live in `%APPDATA%\mobile-crawler` (Windows), `~/Library/Application Support/mobile-crawler` (macOS) or `~/.local/share/mobile-crawler` (Linux). The CLI and GUI share them.

## crawl

```powershell
mobile-crawler-cli crawl --device <id|last> --package <pkg|last> --model <model> [options]
```

| Option | Meaning |
|---|---|
| `--device` (required) | ADB device id (`adb devices` / `list devices`), or `last` for the device last used in the GUI |
| `--package` (required) | App package (`list apps -d <device>`), or `last`. Repeat to crawl several apps as a batch |
| `--model` (required) | AI model name |
| `--provider` | `gemini`, `openrouter` or `ollama` (default: configured provider) |
| `--steps N` | Max steps per app |
| `--duration SECONDS` | Max duration per app. Mutually exclusive with `--steps`; with neither, the configured limit is used |
| `--enable-traffic-capture` | PCAPdroid capture during the crawl |
| `--enable-video-recording` | Record the device screen |
| `--enable-mobsf-analysis` | Run MobSF static analysis after the crawl |
| `--no-report` | Skip generating the run report |
| `--log-level debug\|info\|warning\|error` | Minimum level of log events printed to stdout (default: `log_level` setting) |
| `--human-fallback / --no-human-fallback` | Ask a human in the terminal when the agent is stuck, or not |
| `--parser-mode accessibility\|boost\|omniparser` | UI parser mode |
| `--reasoning-mode / --no-reasoning-mode` | Crawler agent Reasoning Mode on/off |
| `--exploration-objective TEXT` | Exploration Objective |
| `--restart-app / --no-restart-app` | Force-stop the app first so the run starts at its launch screen (data kept), or resume where it is (default: on) |
| `--step-by-step` | Pause after each step, print what it did on stderr, wait for Enter |

All flags apply to that invocation only; they are never saved to the settings store. Without a flag, the persisted setting (as set in the GUI or with `config set`) is used.

Output: lifecycle and log events as JSON lines on stdout; warnings (pre-run checks such as Portal off or Phoenix down), prompts and summaries on stderr.

```powershell
# 15 steps with Gemini
mobile-crawler-cli crawl --device emulator-5554 --package com.example.app `
  --provider gemini --model gemini-3.8-flash --steps 15

# 5 minutes, OmniParser parsing, no report
mobile-crawler-cli crawl --device emulator-5554 --package com.example.app `
  --provider openrouter --model <model> --duration 300 --parser-mode omniparser --no-report

# Same device and app as last time in the GUI, watching step by step
mobile-crawler-cli crawl --device last --package last --model gemini-3.8-flash --step-by-step
```

### Batch crawls

Repeat `--package` to crawl apps one after another with the same settings; each app gets its own run.

```powershell
mobile-crawler-cli crawl --device emulator-5554 --package com.a.app --package com.b.app --package com.c.app `
  --provider gemini --model gemini-3.8-flash --duration 600 --no-human-fallback
```

- Before each app the batch checks the device is still connected and the package is installed; a missing app is skipped, the previous app is force-stopped.
- An app that errors doesn't stop the batch; a disconnected device or Ctrl+C does.
- Ends with a `batch_completed` JSON event on stdout and a summary table on stderr.
- Exit code 0 only if every app's run completed; 130 on Ctrl+C.
- Pass `--no-human-fallback` for unattended batches, otherwise an unanswered prompt waits out its timeout.

### API keys

The LLM key is looked up in the settings store first, then the environment:

| Provider | Setting | Environment |
|---|---|---|
| gemini | `gemini_api_key` | `GEMINI_API_KEY`, `GOOGLE_API_KEY` |
| openrouter | `openrouter_api_key` | `OPENROUTER_API_KEY` |
| OmniParser (Replicate) | `replicate_api_key` | `REPLICATE_API_KEY` |

Store one with `mobile-crawler-cli config set gemini_api_key <key>`.

## list

```powershell
mobile-crawler-cli list runs [-n 10] [--format table|json]
mobile-crawler-cli list devices
mobile-crawler-cli list apps -d <device> [--no-names]
```

- `runs` / `devices` default to 10 items; `apps` lists all third-party packages (valid `crawl --package` values).
- `--no-names` skips resolving app names (faster; the first lookup pulls the APK).

## stats

```powershell
mobile-crawler-cli stats <run_id> [--format table|json]
```

Same record as the GUI's Run History "View Stats". Saved when a crawl completes.

## report

```powershell
mobile-crawler-cli report <run_id> [-o report.html]
```

Writes the HTML report and the analysis folder (`analysis.md`, `steps.jsonl`, `run.json`) into the run's session folder, pulling Phoenix/Langfuse telemetry back in. `crawl` already does this unless `--no-report`.

## mobsf-scan

```powershell
mobile-crawler-cli mobsf-scan <run_id>
```

Scans the APK stored in the run's session folder (only there if MobSF already ran for that run); never pulls from the device. Starts the MobSF Docker container if needed.

## delete

```powershell
mobile-crawler-cli delete <run_id> [-y]
```

Deletes the run and all its data; `-y` skips the confirmation.

## scenarios

Guided Scenarios are the pages/flows a crawl tries to visit, stored per package. All subcommands take `-p/--package`. Indexes are 1-based.

```powershell
mobile-crawler-cli scenarios list     -p com.example.app
mobile-crawler-cli scenarios add      -p com.example.app "Open settings" [--position 2]
mobile-crawler-cli scenarios edit     -p com.example.app 2 "Open account settings"
mobile-crawler-cli scenarios move     -p com.example.app 3 1
mobile-crawler-cli scenarios remove   -p com.example.app 2
mobile-crawler-cli scenarios set      -p com.example.app "Sign up" "Search" "Checkout"   # no TEXT clears the list
mobile-crawler-cli scenarios set      -p com.example.app --website-url https://example.com  # only sets the URL override
mobile-crawler-cli scenarios generate -p com.example.app [--website-url URL] [--provider P] [--model M] [--exploration-objective TEXT]
```

`generate` builds the list with the LLM from the app's Play Store listing / website and replaces the current list on success; on failure it keeps the list and exits non-zero.

## portal

The `boost` and `accessibility` parser modes need Mobilerun Portal installed with its accessibility service on. The Portal app's sign-in, API key, IP and token are not needed.

```powershell
mobile-crawler-cli portal status  --device <id>   # read-only check
mobile-crawler-cli portal enable  --device <id>   # turn the accessibility service on over adb (installs if missing)
mobile-crawler-cli portal install --device <id>   # download the pinned release, (re)install, enable
```

Force-stopping Portal turns its service off; run `portal enable` again.

## config

```powershell
mobile-crawler-cli config list
mobile-crawler-cli config get <key>
mobile-crawler-cli config set <key> <value>
```

- Values are parsed as JSON, then bool/int/float, else kept as a string.
- Keys containing `api_key`, `key`, `token`, `secret` or `password` are stored encrypted; `config list` shows them as `[ENCRYPTED]`.
- Lookup order: per-run flags → settings store → `CRAWLER_<KEY>` environment variable → built-in default (`src/mobile_crawler/config/defaults.py`).

Useful keys: `ai_provider`, `ai_model`, `max_crawl_steps`, `max_crawl_duration_seconds`, `ui_parser_mode`, `restart_app_before_run`, `crawler_reasoning_mode`, `log_level`, `pcapdroid_api_key`, `mobsf_api_url`, `mobsf_api_key`.
