# Mobile Crawler

Mobile Crawler is a developer tool for running AI-assisted exploration of Android apps. The application owns the UI, CLI, run/session persistence, settings, logs, and reporting infrastructure; the active exploration runtime is driven by the internalized `crawler_agent` package under `src/mobile_crawler/domain/crawler_agent`.

Mobile Crawler runs directly through the internalized agent runtime.

## Quick Start

```powershell
git clone <repository-url>
cd mobile-crawler

python -m venv .venv312
.\.venv312\Scripts\Activate.ps1

# Install Mobile Crawler and all its internalized crawler_agent dependencies
pip install -e .
```

For development tools:

```powershell
pip install -e ".[dev]"
```

Run the GUI:

```powershell
mobile-crawler-gui
```

When "Enable MobSF Analysis" is turned on in Settings, the GUI automatically starts the managed MobSF Docker container on launch (and warns if Docker or MobSF is unavailable). Otherwise it runs without MobSF.

Run a crawl from the CLI:

```powershell
mobile-crawler-cli crawl --device emulator-5554 --package com.example.app --provider gemini --model gemini-3.8-flash --steps 15
```

## Current Project State

- The canonical repository is `https://github.com/ganainy/ai-mobile-ui-crawler`.
- The canonical architecture document is `docs/ARCHITECTURE.md`.
- Completed planning files have been removed. Keep future durable state in this README, `docs/ARCHITECTURE.md`, active `specs/*` documents, and `.codex/project-memory/CHANGELOG.md`.
- Recent UI settings work added AI Crawler tabs, local/Replicate OmniParser backend settings, a remote OmniParser warm-up button, app test credential fields for address/email/phone, a reset button for the exploration objective, and tighter spin-box steps for crawl limits.
- `AGENTS.md` is currently absent from the workspace. If project-wide agent instructions are recreated, keep them concise and aligned with `.codex/project-memory/CHANGELOG.md`.

## Requirements

- Python 3.12. `pyproject.toml` currently requires `>=3.12,<3.13`.
- Android device or emulator reachable through ADB.
- AI provider credentials for the selected provider. Current config mapping supports Gemini, OpenAI, Anthropic, Ollama, and OpenRouter in `CrawlerAgentService`.

Optional integrations:

- PCAPdroid for traffic capture.
- MobSF server for static APK analysis.
- Android screen recording support for session video capture.
- Replicate or local OmniParser configuration when using fallback-capable parser modes such as `boost`. See `docs/architecture/readmes/local-omniparser-setup.md` for local setup notes.

## Prepare an Android Device for ADB

Mobile Crawler needs the target device or emulator to be visible through ADB before you start the GUI or CLI crawl.

Install Android SDK Platform Tools first if `adb` is not already available in PowerShell:

```powershell
adb version
```

On the Android device:

1. Open Settings > About phone.
2. Tap Build number seven times to enable Developer options.
3. Open Settings > System > Developer options. The exact path varies by Android version and device vendor.
4. Enable Developer options.
5. Enable USB debugging for a USB connection.
6. Enable Wireless debugging if you want to connect over Wi-Fi.

For USB debugging:

```powershell
adb devices
```

Accept the authorization prompt on the device. The device should appear as `device`, not `unauthorized`.

For wireless debugging on Android 11 or newer, keep the device and PC on the same network, open Wireless debugging on the device, and use the IP address and port shown there:

```powershell
adb pair 172.20.10.4:<pairing-port>
adb connect 172.20.10.4:5555
adb devices
```

Use the connected device ID in crawl commands. For example:

```powershell
mobile-crawler-cli crawl --device 172.20.10.4:5555 --package com.example.app --provider gemini --model gemini-3.8-flash --steps 15
```

For older Android versions or USB-first wireless setup, connect over USB once, then run:

```powershell
adb tcpip 5555
adb shell ip addr show wlan0
adb connect 172.20.10.4:5555
adb devices
```

Replace `172.20.10.4` with the device IP address reported by Android or `adb shell ip addr show wlan0`.

## Usage

### GUI

The GUI entry point is the `mobile-crawler-gui` console script (`mobile_crawler.ui.main_window:run`). On launch it starts the managed MobSF Docker container when MobSF analysis is enabled. `MainWindow` builds the PySide6 interface, creates services and repositories, bridges Python logging into the log panel, creates run records, and launches crawl execution on a worker thread.

The UI exposes device selection, app selection, AI model/provider selection, crawl controls, settings, logs, run history, statistics, and AI monitoring. Settings are persisted through `UserConfigStore` and copied into a `ConfigManager` when a crawl starts.

### CLI

The CLI entry point is `mobile-crawler-cli` (a console script installed into the venv by `pip install -e .`), which calls `mobile_crawler.cli.main.run()`. Commands: `crawl`, `list`, `stats`, `report`, `mobsf-scan`, `delete`, `scenarios`, `a11y-portal`, `config`.

**Full reference with every command and flag: [docs/cli.md](docs/cli.md).**

```powershell
mobile-crawler-cli crawl --device emulator-5554 --package com.example.app `
  --provider gemini --model gemini-3.8-flash --steps 15

# Crawl several apps one after another, 10 minutes each; every app gets its own run
mobile-crawler-cli crawl --device emulator-5554 --package com.a.app --package com.b.app `
  --provider gemini --model gemini-3.8-flash --duration 600 --no-human-fallback
```

Command-line settings apply to that invocation only; they are never saved to the settings store.

## MobSF Static Analysis

Mobile Crawler can run MobSF static APK analysis after a successful crawl or manually from the `Run MobSF` button in Run History. MobSF itself must be running separately; the app connects to its REST API, pulls the target APK from the selected device, uploads it, starts a static scan, and saves the JSON/PDF reports in the run session.

The analysis supports regular APKs and split APK installs. Split APKs are pulled from the device, packaged into a `.apks` archive, and uploaded to MobSF.

Artifacts are saved under the run folder:

```text
output_data/
└── run_{ID}_{YYYYMMDD_HHMMSS}/
    ├── apks/
    │   ├── com.example.app.apk
    │   └── com.example.app.apks
    └── reports/
        └── mobsf/
            ├── {mobsf_hash}_report.json
            └── {mobsf_hash}_report.pdf
```

## CrawlerAgent Traffic Capture and TLS Decryption

Mobile Crawler can start PCAPdroid before Crawler begins crawling, request TLS decryption, stop capture during crawl cleanup, and save the resulting `.pcap` file in the run session.

Phone setup:

1. Install PCAPdroid from Google Play on the Android device.
2. Open PCAPdroid settings and enable TLS decryption.
3. When prompted by PCAPdroid, install PCAPdroid-mitm.
4. Install the generated or custom PCAPdroid CA certificate on the device.
5. In PCAPdroid, tap the settings icon, scroll to the bottom, tap Control Permissions, and generate an API key.
6. Paste the API key into the Mobile Crawler app UI under Settings > Integrations.
7. Enable Traffic Capture in Mobile Crawler before starting a crawl.

CLI users can pass `--enable-traffic-capture`. The PCAPdroid API key can come from persisted config or `CRAWLER_PCAPDROID_API_KEY`; without it, PCAPdroid may require on-device consent.

Capture results are saved under:

```text
output_data/run_{ID}_{YYYYMMDD_HHMMSS}/pcap/
```

TLS decryption is best effort. QUIC, certificate pinning, apps that do not trust user CAs, and apps with custom encryption may still produce traffic that does not decrypt cleanly.

### Install Docker Desktop on Windows

1. Install Docker Desktop for Windows from <https://www.docker.com/products/docker-desktop/>.
2. During installation, enable the WSL 2 backend when prompted.
3. Restart Windows if Docker asks you to.
4. Start Docker Desktop and wait until it shows that Docker Engine is running.
5. Verify Docker from PowerShell:

```powershell
docker --version
docker info
```

If `docker info` fails, open Docker Desktop once and let it finish initializing. On some Windows systems, you may also need to enable WSL 2 and virtualization in BIOS/UEFI.

### Install and Run MobSF Docker Image

Pull the MobSF image:

```powershell
docker pull opensecurity/mobile-security-framework-mobsf
```

Run MobSF manually on `http://localhost:8000`:

```powershell
docker run --rm -it --name mobile-crawler-mobsf -p 8000:8000 opensecurity/mobile-security-framework-mobsf
```

Keep this PowerShell window open while using MobSF analysis. To stop MobSF, press `Ctrl+C` in that window.

Alternatively, run the GUI normally; when "Enable MobSF Analysis" is on, it starts the managed container automatically (with the expected container name), saves the API key to `.mobsf_api_key` when it can extract it from the container logs, and on close offers to stop the container it started.

### Configure MobSF API Key

MobSF requires an API key for REST calls. Mobile Crawler resolves the key automatically in this order:

1. `.mobsf_api_key` in the repository root or a parent directory.
2. Docker logs from the managed `mobile-crawler-mobsf` container.
3. Legacy `CRAWLER_MOBSF_API_KEY` / `mobsf_api_key` sources for backward compatibility.
4. Fail with a clear setup error if no key is available.

To create the key file manually, copy the REST API key printed in the MobSF Docker logs and write it to `.mobsf_api_key`:

```powershell
Set-Content -Path .mobsf_api_key -Value "<your_mobsf_api_key>"
```

The default MobSF URL is `http://localhost:8000`. Change the MobSF API URL in the GUI settings only if you run MobSF elsewhere.

### Run MobSF Analysis

Automatic after crawl:

```powershell
mobile-crawler-cli crawl --device emulator-5554 --package com.example.app --provider gemini --model gemini-3.8-flash --enable-mobsf-analysis
```

In the GUI, enable MobSF analysis in Settings before starting a crawl. To run MobSF automatically after each successful, non-cancelled crawl, also enable the "Automatically run after each successful crawl" checkbox; otherwise MobSF stays available for manual runs only. If MobSF fails, the crawl remains completed and the failure is written to logs.

Manual from history:

1. Open the GUI.
2. Select a completed run in Run History.
3. Click `Run MobSF`.
4. Wait for the background analysis to finish.

The manual button uses the run's stored device ID and package name, so the same device or emulator should still be available through ADB.

## Runtime Architecture

The current crawl flow is:

1. `mobile-crawler-cli` starts the CLI, or `mobile-crawler-gui` starts the GUI.
2. The CLI `crawl` command or GUI `MainWindow` creates a run record, prepares `ConfigManager`, repositories, and `SessionFolderManager`, then runs `CrawlerLoop`.
3. `CrawlerLoop` creates a timestamped session folder, stores the session path on the run, emits lifecycle events, attaches crawler-agent logging, and calls `CrawlerAgentService.execute_exploration_task()`.
4. `CrawlerAgentService` translates Mobile Crawler settings into the internal runtime's `CrawlerConfig`, ensures the target package is active through ADB preflight checks, creates a `CrawlerAgent`, and runs the crawler-agent workflow.
5. During execution, Mobile Crawler consumes tool events for step phase tracking, forwards logs and stdout to UI/CLI listeners, handles duration limits and cancellation, tracks action outcomes from shared state, retries app-crash-like failures, and cleans up async LLM clients.
6. `CrawlerLoop` updates final run stats and emits completion or error events.
7. If MobSF analysis is enabled and the crawl completed successfully, `CrawlerLoop` runs MobSF static analysis and logs the generated report paths.

`CrawlerLoop` is intentionally thin. It manages Mobile Crawler run state, session folders, event forwarding, cancellation, logging, cleanup, and final stats; it does not own the exploration loop.

## How the Agent Runtime is Used

The agent runtime is fully internalized within the `mobile_crawler` package at `src/mobile_crawler/domain/crawler_agent/`.
Imports from the agent runtime resolve directly under the `mobile_crawler.domain.crawler_agent` namespace (e.g., `from mobile_crawler.domain.crawler_agent import CrawlerConfig, CrawlerAgent, ToolExecutionEvent`). The dynamic runtime injection that inserted the external path into `sys.path` has been completely removed.

Mobile Crawler does not own the agent runtime's core exploration loop. The internalized `crawler_agent` package owns screenshot and UI-state capture, LLM planning and execution, agent workflows, and ADB-backed device actions.

Mobile Crawler wraps the internalized `crawler_agent` with:

- Run and session persistence.
- GUI/CLI event listeners.
- SQLite repositories and configuration storage.
- Session folders for screenshots, reports, PCAP files, videos, logs, data, and APKs.
- Logging forwarding to JSONL and UI logs.
- Target-app preflight and app-switch/context guards.
- Step phase tracking and action verification hooks.
- Duration limits, cancellation requests, crash recovery, and LLM client cleanup.
- Optional MobSF, PCAPdroid, video, and report/artifact infrastructure.

For a detailed explanation of the Manager/Executor decision loop, FastAgent mode, timing costs, and speed/quality tuning options, see `docs/architecture/readmes/crawler-agent-decision-loop.md`.

## How UI Parsing Works With crawler_agent

`crawler_agent` mainly uses Android Accessibility APIs, not pure screenshot vision first. Mobile Crawler passes parser settings into the agent through `CrawlerAgentService`, and the agent runtime owns active screenshot capture, UI parsing, formatted state text, indexed element lookup, and ADB-backed action execution during the crawl.

In the default `boost` mode, the agent uses the accessibility tree first and falls back to OmniParser only when accessibility metadata is unavailable or insufficient.

The `ui_parser_mode` setting controls which UI source the agent uses:

- `omniparser`: always parse screenshots with OmniParser.
- `boost` (default): use accessibility data first, otherwise fall back to OmniParser.
- `accessibility`: use accessibility data only.

When OmniParser is used, the agent converts OmniParser bounding boxes into indexed UI elements with tap-ready bounds before presenting them to the LLM agent. Local OmniParser parses use `/parse/` by default, fall back to `/parse` only when needed, and honor `omniparser_local_parse_timeout_seconds` (120 seconds by default for slower CPU inference).

For the Replicate backend, the Settings panel includes a **Warm Up Remote OmniParser** button in the UI Parser section. It sends a mock screenshot to the same Replicate OmniParser model used by crawls, runs in the background, and reports completion or failure in the UI.

## Project Boundaries

Mobile Crawler owns:

- PySide6 GUI and Click CLI.
- Device and app selection UX.
- Settings, secrets, defaults, and provider selection.
- SQLite storage for runs, screens, step logs, transitions, stats, AI interactions, and step phases.
- Session folder creation and artifact layout.
- Reporting, run history, MobSF integration, PCAPdroid integration, and video capture hooks.
- Agent orchestration, log forwarding, lifecycle events, and run-level status.

The internalized `crawler_agent` owns:

- `CrawlerAgent` and active UI-agent execution.
- Manager, executor, fast-agent, app-opener, and structured-output workflows.
- Prompt templates and agent internals.
- Android driver, state provider, UI action tools, and ADB-backed device actions.
- LLM adapter implementations used by the agent runtime.

## Configuration Notes

Default values live in `src/mobile_crawler/config/defaults.py`. Notable defaults include:

- `max_crawl_steps`: `15`
- `max_crawl_duration_seconds`: `600`
- `use_crawler_agent`: `True`
- `crawler_reasoning_mode`: `True`
- `crawler_streaming`: `False`
- `crawler_telemetry_enabled`: `False`
- `ui_parser_mode`: `boost`
- `omniparser_backend`: `replicate`
- optional traffic capture, video recording, and MobSF analysis disabled by default

API keys can come from persisted secrets/settings or environment variables. `CrawlerAgentService` resolves provider keys and passes them into crawler-agent LLM profiles.

Telemetry key configuration:

- `CRAWLER_POSTHOG_PROJECT_API_KEY`: PostHog project key used by crawler-agent telemetry.
- `DROIDRUN_POSTHOG_PROJECT_API_KEY`: legacy fallback key name retained for compatibility.
- `DROIDRUN_TELEMETRY_ENABLED`: telemetry on/off switch (`true` by default when key is present).

## Data Organization

`SessionFolderManager` creates per-run folders under the app data directory's `output_data` folder by default:

Every report of a run is in its `reports/` folder; raw artifacts stay in their own folders:

```text
output_data/
└── run_{ID}_{YYYYMMDD_HHMMSS}/
    ├── reports/
    │   ├── run_report.html          # Run Report, human-readable half
    │   ├── analysis/                # Analysis Bundle: analysis.md, steps.jsonl, run.json
    │   ├── mobsf/                   # MobSF JSON/PDF
    │   ├── config_snapshot.json
    │   └── crawler_trace.jsonl
    ├── screenshots/
    ├── pcap/
    ├── videos/
    └── apks/
```

The paths are defined in one place, `domain/run_folder_layout.py`. Older run folders (with `analysis/`, `data/`, `logs/` and `reports/report_run_<id>.html`) are moved to this layout by `scripts/migrate_run_folders.py` (`--dry-run` to preview).

The session path is stored on the run record so the UI can resolve artifacts later.

## Current Limitations

- Pause, resume, step-by-step mode, and manual next-step advancement are not supported. The current `CrawlerLoop` methods emit debug messages for those controls and do not pause the agent workflow.
- The `use_crawler_agent` setting remains in the UI/config, but the current `CrawlerLoop` implementation delegates traversal to the internalized `crawler_agent`.

## Development

```powershell
pytest
ruff check .
black .
pytest --cov=mobile_crawler --cov-report=html
```

Documentation-only README edits do not require code tests. For runtime changes, prefer targeted tests around the modified module and a smoke run through the CLI or GUI path.

## Documentation Memory

Use `.codex/project-memory/CHANGELOG.md` as the compact project-state memory for future Codex sessions. Completed planning docs should not be recreated just for history; preserve implemented decisions in `docs/ARCHITECTURE.md`, active specs, this README, and the changelog.

Other README-style documents are grouped under `docs/architecture/readmes/` so the root stays focused as the main project entry point.

## License

MIT
