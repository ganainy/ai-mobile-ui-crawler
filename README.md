# Mobile Crawler

Mobile Crawler is a developer tool for running AI-assisted exploration of Android apps. The application owns the UI, CLI, run/session persistence, settings, logs, and reporting infrastructure; the active exploration runtime is delegated to the DroidRun submodule in `external/droidrun`.

Mobile Crawler runs through the editable DroidRun runtime in `external/droidrun`.

## Quick Start

```powershell
git clone <repository-url>
cd mobile-crawler

git submodule update --init --recursive

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -e .
# Install DroidRun dependencies from the local submodule, not the published package.
pip install -e external/droidrun
```

For development tools:

```powershell
pip install -e ".[dev]"
```

Run the GUI:

```powershell
python run_ui.py
# or, after editable install:
mobile-crawler-gui
```

Run a crawl from the CLI:

```powershell
python run_cli.py crawl --device emulator-5554 --package com.example.app --provider gemini --model gemini-1.5-flash --steps 15
# or, after editable install:
mobile-crawler-cli crawl --device emulator-5554 --package com.example.app --provider gemini --model gemini-1.5-flash --steps 15
```

Optional startup helper:

```powershell
.\scripts\start.ps1          # start MobSF, then the UI
.\scripts\start.ps1 -NoMobsf # start only the UI
.\scripts\start.ps1 -UiOnly  # start only the UI
```

## Requirements

- Python 3.11+ for the current DroidRun-backed runtime. The Mobile Crawler package metadata allows Python 3.9+, but the vendored DroidRun submodule declares Python 3.11 to 3.13.
- Android device or emulator reachable through ADB.
- AI provider credentials for the selected provider. Current config mapping supports Gemini, OpenAI, Anthropic, Ollama, and OpenRouter in `DroidRunAgentService`.
- `external/droidrun` initialized as a git submodule.

Optional integrations:

- PCAPdroid for traffic capture.
- MobSF server for static APK analysis.
- Android screen recording support for session video capture.
- Replicate or local OmniParser configuration when using the default `ui_parser_mode`.

## Usage

### GUI

The GUI entry point is `run_ui.py`, which inserts `src` into `sys.path` and calls `mobile_crawler.ui.main_window.run()`. `MainWindow` builds the PySide6 interface, creates services and repositories, bridges Python logging into the log panel, creates run records, and launches crawl execution on a worker thread.

The UI exposes device selection, app selection, AI model/provider selection, crawl controls, settings, logs, run history, statistics, and AI monitoring. Settings are persisted through `UserConfigStore` and copied into a `ConfigManager` when a crawl starts.

### CLI

The CLI entry point is `run_cli.py`, which calls `mobile_crawler.cli.main.run()`. The `crawl` command:

1. Creates the app data directory and configuration store.
2. Applies command-line settings such as device, package, model, provider, step or duration limits, and optional feature flags.
3. Migrates the SQLite schema and creates a run record.
4. Creates a `CrawlerLoop` with a JSON event listener.
5. Runs the crawler and emits lifecycle/debug events as JSON on stdout.

Useful flags:

```powershell
mobile-crawler-cli crawl `
  --device emulator-5554 `
  --package com.example.app `
  --provider gemini `
  --model gemini-1.5-flash `
  --steps 15

mobile-crawler-cli crawl --device emulator-5554 --package com.example.app --provider openrouter --model <model> --duration 300
mobile-crawler-cli crawl --device emulator-5554 --package com.example.app --provider gemini --model gemini-1.5-flash --enable-traffic-capture
mobile-crawler-cli crawl --device emulator-5554 --package com.example.app --provider gemini --model gemini-1.5-flash --enable-video-recording
mobile-crawler-cli crawl --device emulator-5554 --package com.example.app --provider gemini --model gemini-1.5-flash --enable-mobsf-analysis
```

## Runtime Architecture

The current crawl flow is:

1. `run_cli.py` or `run_ui.py` starts the CLI or GUI.
2. The CLI `crawl` command or GUI `MainWindow` creates a run record, prepares `ConfigManager`, repositories, and `SessionFolderManager`, then runs `CrawlerLoop`.
3. `CrawlerLoop` creates a timestamped session folder, stores the session path on the run, emits lifecycle events, attaches DroidRun logging, and calls `DroidRunAgentService.execute_exploration_task()`.
4. `DroidRunAgentService` translates Mobile Crawler settings into a DroidRun `DroidConfig`, ensures the target package is active through ADB preflight checks, creates a DroidRun `DroidAgent`, and runs the DroidRun workflow.
5. During execution, Mobile Crawler consumes DroidRun tool events for step phase tracking, forwards logs and stdout to UI/CLI listeners, handles duration limits and cancellation, tracks action outcomes from DroidRun shared state, retries app-crash-like failures, and cleans up async LLM clients.
6. `CrawlerLoop` updates final run stats and emits completion or error events.

`CrawlerLoop` is intentionally thin. It manages Mobile Crawler run state, session folders, event forwarding, cancellation, logging, cleanup, and final stats; it does not own the exploration loop.

## How DroidRun Is Used

DroidRun is currently loaded from `external/droidrun`. `DroidRunAgentService._ensure_droidrun_import()` inserts that submodule path into `sys.path` before importing DroidRun classes such as `DroidConfig`, `DroidAgent`, and `ToolExecutionEvent`.

Mobile Crawler does not own DroidRun's core exploration loop. DroidRun owns screenshot and UI-state capture, LLM planning and execution, agent workflows, and ADB-backed device actions.

Mobile Crawler wraps DroidRun with:

- Run and session persistence.
- GUI/CLI event listeners.
- SQLite repositories and configuration storage.
- Session folders for screenshots, reports, PCAP files, videos, logs, data, and APKs.
- DroidRun log forwarding to JSONL and UI logs.
- Target-app preflight and app-switch/context guards.
- Step phase tracking and action verification hooks.
- Duration limits, cancellation requests, crash recovery, and LLM client cleanup.
- Optional MobSF, PCAPdroid, video, and report/artifact infrastructure.

## How OmniParser Works With DroidRun

Mobile Crawler passes OmniParser settings into DroidRun through `DroidRunAgentService` when it builds the DroidRun `DroidConfig`. DroidRun then owns the active screenshot capture, UI parsing, formatted state text, indexed element lookup, and ADB-backed action execution used during the crawl.

The `ui_parser_mode` setting controls which UI source DroidRun uses:

- `omniparser`: always parse screenshots with OmniParser.
- `boost`: use accessibility data when it has enough elements, otherwise fall back to OmniParser.
- `accessibility`: use accessibility data only.

When OmniParser is used, DroidRun converts OmniParser bounding boxes into indexed UI elements with tap-ready bounds before presenting them to the agent. Mobile Crawler's local `OmniParserClient` and `UIContextManager` appear to be auxiliary diagnostic/cache code; they are not the active crawl path.

## Project Boundaries

Mobile Crawler owns:

- PySide6 GUI and Click CLI.
- Device and app selection UX.
- Settings, secrets, defaults, and provider selection.
- SQLite storage for runs, screens, step logs, transitions, stats, AI interactions, and step phases.
- Session folder creation and artifact layout.
- Reporting, run history, MobSF integration, PCAPdroid integration, and video capture hooks.
- DroidRun orchestration, log forwarding, lifecycle events, and run-level status.

DroidRun owns:

- `DroidAgent` and active UI-agent execution.
- Manager, executor, fast-agent, app-opener, and structured-output workflows.
- Prompt templates and agent internals.
- Android driver, state provider, UI action tools, and ADB-backed device actions.
- LLM adapter implementations used by the agent runtime.

## Configuration Notes

Default values live in `src/mobile_crawler/config/defaults.py`. Notable defaults include:

- `max_crawl_steps`: `15`
- `max_crawl_duration_seconds`: `600`
- `use_droidrun_agent`: `True`
- `droidrun_reasoning_mode`: `True`
- `droidrun_streaming`: `False`
- `droidrun_telemetry_enabled`: `False`
- `ui_parser_mode`: `omniparser`
- `omniparser_backend`: `replicate`
- optional traffic capture, video recording, and MobSF analysis disabled by default

API keys can come from persisted secrets/settings or environment variables. `DroidRunAgentService` resolves provider keys and passes them into DroidRun LLM profiles.

## Data Organization

`SessionFolderManager` creates per-run folders under the app data directory's `output_data` folder by default:

```text
output_data/
└── run_{ID}_{YYYYMMDD_HHMMSS}/
    ├── screenshots/
    ├── reports/
    ├── pcap/
    ├── videos/
    ├── logs/
    ├── data/
    └── apks/
```

The session path is stored on the run record so the UI can resolve artifacts later.

## Current Limitations

- Pause, resume, step-by-step mode, and manual next-step advancement are not supported in DroidRun mode. The current `CrawlerLoop` methods emit debug messages for those controls and do not pause the DroidRun workflow.
- Current crawl execution is DroidRun-first through the editable runtime in `external/droidrun`.
- The `use_droidrun_agent` setting remains in the UI/config, but the current `CrawlerLoop` implementation delegates traversal to DroidRun.
- Removing `external/droidrun` requires vendoring or rewriting the active UI-agent runtime, including agent workflows, prompts, state capture, LLM adapters, and Android action tools.

## Development

```powershell
pytest
ruff check .
black .
pytest --cov=mobile_crawler --cov-report=html
```

Documentation-only README edits do not require code tests. For runtime changes, prefer targeted tests around the modified module and a smoke run through the CLI or GUI path.

## License

MIT
