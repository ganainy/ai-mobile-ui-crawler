---
updated: 2026-09-23
---
# CLI Reference

Run the CLI from the project's virtual environment, the same one the GUI uses (`.venv312`). Activate it first in each new terminal, from the repo root:

```powershell
.\.venv312\Scripts\Activate.ps1
```

Then run `mobile-crawler-cli` (installed into the venv by `pip install -e .`). Without activating, call it by path: `.\.venv312\Scripts\mobile-crawler-cli.exe`. A global Python is missing the dependencies.

## Quick start

A first short crawl, from a terminal with the venv active:

1. **Check the device is connected.** Its status must be `device`. If it's missing, see "Prepare an Android Device for ADB" in the [README](../README.md).
   ```powershell
   mobile-crawler-cli list devices
   ```
2. **Pick the app to crawl** from the device's installed apps, using its package name.
   ```powershell
   mobile-crawler-cli list apps -d <device-id>
   ```
3. **Save the AI API key** (only once; it's stored encrypted and the GUI uses it too).
   ```powershell
   mobile-crawler-cli config set gemini_api_key <your-key>
   ```
4. **Set up how the crawler reads the screen.** Use option A if you can; B only if Portal can't run on the device.

   **A. Accessibility Portal (recommended, free).** Portal (the "Mobilerun Portal" app) must be **installed on the device with its accessibility service turned on**. The default parser mode (`boost`) reads the screen through it.
   ```powershell
   mobile-crawler-cli a11y-portal enable --device <device-id>   # installs Portal if missing, then turns its service on
   mobile-crawler-cli a11y-portal status --device <device-id>   # must report Portal as ready
   ```
   Keep the phone unlocked and watch it while this runs:
   - **Install warning:** if Play Protect or the phone warns about an app from an unknown source, choose to install anyway (e.g. *More details > Install anyway*). Some phones first ask you to allow installing over USB.
   - **Accessibility warning:** if `status` still says the service is off, turn it on by hand: *Settings > Accessibility > Installed apps* (stock Android: *Downloaded apps*) *> Mobilerun Portal*, switch it on and tap **Allow** on the "full control of your device" warning. If the switch is greyed out: *Settings > Apps > Mobilerun Portal > ⋮ > Allow restricted settings*, then try again. The command prints these steps when Portal isn't ready.
   - The service turns off when Portal is force-stopped or updated; run `a11y-portal enable` again. The Portal app's sign-in, API key, IP and token are not needed.

   **B. Without Portal: OmniParser.** A vision model reads each screenshot instead. Run the crawl with `--parser-mode omniparser`, and set up one of these backends:
   - **Replicate (cloud, the default backend):** create an account at [replicate.com](https://replicate.com), set up billing, create a token under [Account > API tokens](https://replicate.com/account/api-tokens), then save it:
     ```powershell
     mobile-crawler-cli config set replicate_api_key <r8_...>
     ```
   - **Local (needs an NVIDIA GPU and Docker Desktop with WSL2):** build and start the server once (the first run downloads several GB of model weights), then switch the backend. Later crawls start the container themselves.
     ```powershell
     cd docker/omniparser; docker compose up --build
     mobile-crawler-cli config set omniparser_backend local
     ```
     Details and the non-Docker setup: [local-omniparser-setup.md](architecture/readmes/local-omniparser-setup.md).
5. **Run a 5-step crawl.**
   ```powershell
   mobile-crawler-cli crawl --device <device-id> --package <package> --provider gemini --model gemini-3.8-flash --steps 5
   ```
   To watch it step by step, add `--step-by-step`: it pauses after each step, prints what the step did and waits for Enter.
6. **Look at the result.** Find the run id, check its stats, and open the HTML report, which lists every step with its action and screenshot:
   ```powershell
   mobile-crawler-cli list runs -n 1
   mobile-crawler-cli stats <run-id>
   Invoke-Item "$env:APPDATA\mobile-crawler\output_data\run_<run-id>_*\reports\report_run_<run-id>.html"
   ```
   Everything the run produced is in its folder, `%APPDATA%\mobile-crawler\output_data\run_<run-id>_<date>_<time>\`:

   | Path | Contents |
   |---|---|
   | `reports\report_run_<id>.html` / `.json` | The run report, step by step |
   | `screenshots\step_0001.png`, ... | One screenshot per step |
   | `analysis\analysis.md`, `steps.jsonl`, `run.json` | AI-readable summary; `steps.jsonl` has one line per step with the action, the AI's reasoning, timings and success/error |
   | `logs\crawler_trace.jsonl` | Full agent trace |
   | `data\config_snapshot.json` | Settings the run used |
   | `videos\`, `pcap\`, `apks\` + `reports\` | Screen video, traffic capture and MobSF results, when those are on (see below) |

   If the report is missing (e.g. after `--no-report`), rebuild it with `mobile-crawler-cli report <run-id>`.

Settings you save with `config set` or in the GUI become the defaults; flags on `crawl` override them for one run.

### Optional: screen video, traffic capture, MobSF

Each is off by default; add its flag to `crawl` (or turn it on in the GUI's Settings to make it the default). They can be combined.

**Screen video.** Nothing to install; it records with adb `screenrecord` into the run's `videos\` folder.
```powershell
mobile-crawler-cli crawl --device <device-id> --package <package> --provider gemini --model gemini-3.8-flash --steps 5 --enable-video-recording
```

**Network traffic (PCAPdroid).** Saves a `.pcap` of the app's traffic into `pcap\`.
1. Install [PCAPdroid](https://play.google.com/store/apps/details?id=com.emanuelef.remote_capture) from Google Play on the device.
2. In PCAPdroid: settings (gear icon) > scroll to the bottom > *Control Permissions* > generate an API key, and save it:
   ```powershell
   mobile-crawler-cli config set pcapdroid_api_key <key>
   ```
   Without the key PCAPdroid asks for consent on the phone at every start; the crawler tries to accept it for you.
3. Optional, to decrypt HTTPS: in PCAPdroid enable TLS decryption, install the PCAPdroid-mitm add-on and its CA certificate when it prompts you, then `mobile-crawler-cli config set pcapdroid_tls_decryption true`. Apps that pin certificates or use QUIC may still not decrypt.
4. Crawl with the flag. The first time, Android asks to allow PCAPdroid's VPN connection; tap OK.
   ```powershell
   mobile-crawler-cli crawl --device <device-id> --package <package> --provider gemini --model gemini-3.8-flash --steps 5 --enable-traffic-capture
   ```

**Static analysis (MobSF).** After the crawl, pulls the app's APK from the device, scans it in MobSF and saves the JSON/PDF reports into the run's `reports\` (and the APK into `apks\`).
1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (WSL 2 backend) and start it. `docker info` must work.
2. Crawl with the flag. The CLI starts the `mobile-crawler-mobsf` container itself (the first start downloads the MobSF image) and reads its API key from the container logs.
   ```powershell
   mobile-crawler-cli crawl --device <device-id> --package <package> --provider gemini --model gemini-3.8-flash --steps 5 --enable-mobsf-analysis
   ```
3. To scan a finished run again: `mobile-crawler-cli mobsf-scan <run-id>`.

If MobSF fails, the crawl still counts as completed and the error is in the log. Running MobSF by hand and other options: see the README's "MobSF Static Analysis" section.

## Commands

Every command has `--help`:

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
| [`a11y-portal`](#a11y-portal) | Check, enable or install Mobilerun Portal on a device |
| [`config`](#config) | Read and write persisted settings and API keys |

Settings and the database live in `%APPDATA%\mobile-crawler`; the CLI and GUI share them. Only Windows is tested.

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
| `--reasoning-mode / --no-reasoning-mode` | On (default): a Manager LLM call plans the next subgoal, then an Executor LLM call picks the actions (2 calls per step). Off: one FastAgent call decides and acts (faster and cheaper, less reliable on complex flows) |
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

## a11y-portal

The `boost` and `accessibility` parser modes need Mobilerun Portal installed with its accessibility service on. The Portal app's sign-in, API key, IP and token are not needed.

```powershell
mobile-crawler-cli a11y-portal status  --device <id>   # read-only check
mobile-crawler-cli a11y-portal enable  --device <id>   # turn the accessibility service on over adb (installs if missing)
mobile-crawler-cli a11y-portal install --device <id>   # download the pinned release, (re)install, enable
```

Force-stopping Portal turns its service off; run `a11y-portal enable` again.

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
