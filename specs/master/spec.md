# Product Specification: AI-Powered Android Exploration Tool

> **Purpose**: Automated exploration of Android mobile applications using AI-driven visual analysis and intelligent action decisions. The tool captures screenshots, analyzes them via pluggable AI providers, translates analysis into device commands, and executes them via Appium.

---

## Contract

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| **Target app package** | `str` (e.g., `com.example.app`) | User (CLI/UI) | Yes |
| **Connected Android device** | Physical device or emulator via ADB | Appium server | Yes |
| **AI provider config** | Provider name + credentials (`GEMINI_API_KEY`, `OPENROUTER_API_KEY`, or `OLLAMA_BASE_URL`) | User config (DB) | Yes |
| **AI model** | Must be a vision-capable model (image input supported). Non-vision models are not loaded. | Provider model list | Yes |
| **System prompt (optional)** | Customizable goal/instructions for the AI agent | UI settings / config | No (defaults provided) |
| **Crawl limits** | `MAX_CRAWL_STEPS` (default: 15) or `MAX_CRAWL_DURATION_SECONDS` (default: 600) | Config | Yes (at least one) |
| **Allowed external packages (optional)** | List of packages AI may navigate to (OAuth, browsers) | Config | No |
| **Test credentials (optional)** | Email/password for signup/login flows | Config | No |

### Outputs

| Output | Type | Description |
|--------|------|-------------|
| **Screenshots** | `.png` files | Per-step captured screenshots stored in session folder |
| **Action log** | SQLite DB + JSON | Record of each action (type, target, success, duration, reasoning) |
| **Session report** | PDF / console summary | Crawl statistics, unique screens visited, errors encountered |
| **Video recording** | `.mp4` file | Full session recording via Android `screenrecord`; started/stopped automatically by the app |
| **Traffic capture** | `.pcap` file | Network traffic captured via PCAPdroid; started/stopped automatically by the app |
| **MobSF static analysis** | HTML / JSON | Security analysis triggered automatically by the app after crawl; results stored in session folder |

### Data Shapes

#### AI Decision Request (to model)

```json
{
  "screenshot": "<base64 PNG>",
  "exploration_journal": [
    {"step": 1, "action": "Clicked 'Skip'", "outcome": "Success", "screen": "MainActivity"}
  ],
  "is_stuck": false,
  "stuck_reason": null,
  "available_actions": {"click": "...", "input": "...", ...}
}
```

**Note**: The AI receives screenshots for visual analysis. Separately, the system parses XML hierarchy via UiAutomator2 to extract element metadata (bounds, resource IDs) for precise action targeting.

#### AI Decision Response (from model)

```json
{
  "actions": [
    {
      "action": "click",
      "action_desc": "Open login screen",
      "target_bounding_box": {"top_left": [100, 200], "bottom_right": [300, 260]},
      "input_text": null,
      "reasoning": "Login button visible; need to access account features"
    }
  ],
  "signup_completed": false
}
```

- `actions`: Array of 1–12 sequential actions.
- Each action requires `action`, `target_bounding_box` (pixel coordinates), and `reasoning`.
- `target_bounding_box`: Bounding box used to compute tap coordinates (center of box). Can be AI-provided from visual analysis OR derived from XML element bounds parsed via UiAutomator2. When XML elements are available, their bounds provide more accurate targeting than AI-estimated coordinates.
- `signup_completed`: Boolean flag set `true` after successful registration.

#### Action Execution Result

```python
@dataclass
class ActionResult:
    success: bool
    action_type: str
    target: str
    duration_ms: float
    error_message: Optional[str]
    navigated_away: bool  # Did screen change?
```

#### UIElement (from XML hierarchy)

```python
@dataclass
class UIElement:
    """UI element extracted from UiAutomator2 XML hierarchy."""
    element_id: str              # Unique identifier for this element
    bounds: Tuple[int, int, int, int]  # (x1, y1, x2, y2) pixel coordinates
    text: str                    # Visible text content
    content_desc: str            # Accessibility content description
    class_name: str              # Android widget class (e.g., android.widget.Button)
    package: str                 # Package name
    clickable: bool              # Is element clickable?
    visible: bool                # Is element visible on screen?
    enabled: bool                # Is element enabled for interaction?
    resource_id: Optional[str]   # Android resource ID (may be None)
    xpath: Optional[str]         # XPath to element in hierarchy
    center_x: int                # Center X coordinate (derived from bounds)
    center_y: int                # Center Y coordinate (derived from bounds)
```

UIElements are parsed from the XML hierarchy and used for:
- Precise action targeting (tap at element center)
- Element state detection (loading indicators, error states)
- Screen comparison and deduplication

---

## Edge Cases & Failure Modes

| Scenario | Detection | Behavior |
|----------|-----------|----------|
| **App crashes** | `current_package` differs or activity not found | Increment `app_crash_count`; relaunch app; continue |
| **Context loss** | Current package not in allowed list | Press back; if repeated 3×, relaunch app |
| **Screenshot blocked (FLAG_SECURE)** | Black/empty image detected | **Stop crawl with error**; tool cannot operate without screenshots |
| **Loop / stuck** | Same screen visited >2× consecutively with non-navigating actions | Pass `is_stuck=True` + `stuck_reason` to AI; prompt for alternative path |
| **Invalid bounding box** | Coordinates outside screen or missing | Log warning; skip action; continue with next action in batch |
| **AI timeout / error** | HTTP error or timeout from provider | Retry up to 2×; if persistent, pause crawl with `ERROR` state |
| **Invalid AI response** | JSON parse error or schema violation | Log raw response; skip batch; request single action on next step |
| **Device disconnected** | ADB / Appium session lost | Attempt reconnect; if fails, stop crawl with clear error |
| **Max steps/time reached** | Step counter or elapsed time exceeds limit | Graceful shutdown; generate report |

---

## Examples

### Typical Crawl Session

```text
1. User launches UI → selects device "emulator-5554" → enters package "com.example.shop"
2. Clicks "Start Crawl"
3. CrawlerLoop initializes Appium session, launches app
4. Loop iteration:
   a. Capture screenshot
   b. Send to AI (e.g. Gemini)
   c. AI returns: [{"action":"click","target_bounding_box":{"top_left":[50,120],"bottom_right":[200,160]},"reasoning":"Open menu"}]
   d. ActionExecutor taps center of bounding box; records success
   e. Screenshot captured for next iteration
5. After 50 steps, crawl stops; PDF report generated
```

### Multi-Action Batch

```json
{
  "actions": [
    {"action": "click", "target_bounding_box": {"top_left": [80, 400], "bottom_right": [300, 450]}, "input_text": null, "reasoning": "Tap Email field"},
    {"action": "input", "target_bounding_box": {"top_left": [80, 400], "bottom_right": [300, 450]}, "input_text": "test@example.com", "reasoning": "Enter email address"},
    {"action": "click", "target_bounding_box": {"top_left": [80, 480], "bottom_right": [300, 530]}, "input_text": null, "reasoning": "Tap Password field"},
    {"action": "input", "target_bounding_box": {"top_left": [80, 480], "bottom_right": [300, 530]}, "input_text": "SecurePass1!", "reasoning": "Enter password"},
    {"action": "click", "target_bounding_box": {"top_left": [100, 600], "bottom_right": [280, 660]}, "input_text": null, "reasoning": "Tap Login button"}
  ],
  "signup_completed": false
}
```

Executor runs each action sequentially with 0.5s delay; **aborts batch on first failure** (remaining actions not executed).

### Stuck Recovery

```text
Step 12: Screen "MainActivity" visited 3rd time consecutively; last 2 actions stayed on same screen.
StuckDetector sets is_stuck=True, stuck_reason="Visited 3 times; recent actions did not navigate."
AI prompted with stuck context → returns: [{"action":"scroll_down","reasoning":"Reveal hidden content"}]
```

---

## Error Modes & Recovery

| Error | Severity | Recovery |
|-------|----------|----------|
| Appium server unreachable | Critical | Block start; display setup instructions |
| No devices connected | Critical | Block start; prompt user to connect device |
| Invalid API key | Critical | Fail on first AI call; prompt user to update settings |
| Rate limit (AI provider) | Transient | Exponential backoff; retry up to 3× |
| Out of memory (large screenshots) | High | Resize images before AI call; warn user |
| Database locked | Medium | Retry with backoff; if persistent, stop crawl |
| Unknown action type from AI | Low | Log warning; skip action; continue |

---

## Success Criteria

1. **Coverage**: Tool explores ≥80% of reachable screens within configured step/time limit on sample apps.
2. **Stability**: No unhandled exceptions during 100-step crawl on 5 different apps.
3. **Latency**: Average step time (capture → AI → execute) <5s on local Ollama; <8s on cloud providers.
4. **Reporting**: PDF report accurately reflects visited screens, actions taken, and errors encountered.
5. **Extensibility**: New AI provider can be added by implementing `ModelAdapter` without modifying core loop.

---

## Constraints & Assumptions

- **Appium 2.x** with UiAutomator2 driver required.
- **Android 8.0+** devices supported.
- **Single device** per crawl session (parallel crawl sessions not supported).
- **Vision-capable AI model required**: Only models that accept image input are loaded/selectable (e.g., Gemini Pro Vision, llama3.2-vision, GPT-4o via OpenRouter). Text-only models are filtered out. Vision support is detected by querying provider API metadata (e.g., Ollama's `show` command checks for `projector`, `clip`, `vision` indicators).
- **PCAPdroid** must be installed on the device in VPN mode (no root required); the app starts/stops capture via PCAPdroid's intent API.
- **MobSF** server must be reachable (local or remote); static analysis is **optional** and can run on current or past crawl sessions.
- **Video recording** uses Appium's built-in screen recording API (not Android `screenrecord`) to avoid the 3-minute limit.
- **Network access** required for cloud AI providers.
- **Bounding box coordinates** are absolute screen pixels (matching device resolution), not scaled image pixels.

---

## Decisions (Resolved)

1. **iOS support**: Not planned. Android-only via UiAutomator2.
2. **Token limit per AI call**: No enforced limit; cost control is user responsibility.
3. **Custom action plugins**: Not supported. Use built-in action set only.
4. **Credential rotation**: Single AI provider/key per crawl session; no mid-crawl rotation.
5. **Batch failure handling**: If any action in a batch fails, the entire batch aborts; subsequent actions are not executed.
6. **Partial action success**: No adjustment for partially successful actions (e.g., incomplete scroll).
7. **Device rotation**: Not handled; coordinates may become invalid if device rotates mid-crawl.
8. **Screenshot timing**: Screenshot taken at batch start only (before first action); no screenshots between batch actions.
9. **MobSF timing**: Runs in parallel with report generation; does not block. Errors (e.g., split APKs, system apps) logged but crawl continues.
10. **PCAPdroid failure**: If PCAPdroid crashes mid-crawl, error is logged but crawl continues.
11. **Stuck detection threshold**: Based on **consecutive** visits to same screen (>2×), not total visits. Hamming distance threshold (5) is fixed.
12. **Crash recovery**: **Not supported**. If host crashes, run is marked as `ERROR`. Only pause/resume while process is alive.
13. **Secrets encryption**: Uses Fernet symmetric encryption (AES-128-CBC); key derived from machine-bound identifier via PBKDF2.
14. **Report generation**: PDF generated via ReportLab at crawl end. Users can also generate reports for paused/stopped runs on-demand (optional checkbox in UI).
15. **Hybrid XML + Images approach**: The tool uses **both** XML hierarchy data and screenshot images. XML provides precise element metadata (bounds, resource IDs, accessibility info) for accurate Appium action targeting. Screenshots provide visual context for AI decision-making. The AI receives the screenshot; the executor uses XML-derived coordinates for reliable taps.
16. **FLAG_SECURE handling**: If screenshot is blocked, crawl stops with error. No blind mode—screenshots are required.
17. **Run deletion**: Users can delete old runs; associated files (screenshots, video, PCAP, MobSF results) are deleted automatically.
18. **Stale run cleanup**: On startup, attempt to recover partial video/PCAP from crashed runs before marking as `ERROR`.
19. **Default crawl limits**: `MAX_CRAWL_STEPS=15`, `MAX_CRAWL_DURATION_SECONDS=600` (10 minutes).
20. **Session folder timestamp**: Format `DD_MM_HH_MM` (e.g., `10_01_14_30` for Jan 10, 14:30).
21. **Screenshot downscaling**: Screenshots are downscaled before sending to AI to reduce tokens and latency. Max dimension: 1280px (preserving aspect ratio).
22. **Test credentials**: Set via UI fields or CLI command; stored in `user_config.db`; passed to AI in system prompt. Not masked in logs (test-only credentials).
23. **System prompt**: Default prompt provided; user can fully replace it (not append-only).
24. **Appium server**: Always `localhost:4723`. Remote Appium servers not supported.

---

## Integration Details

### PCAPdroid Traffic Capture

PCAPdroid is controlled via Android intent API (ADB shell):

```bash
# Start capture
adb shell am start -n com.emanuelef.remote_capture/.activities.CaptureCtrl \
    -e action start \
    -e pcap_dump_mode pcap_file \
    -e app_filter <target_package> \
    -e pcap_name <filename.pcap> \
    -e api_key <optional_api_key>

# Stop capture
adb shell am start -n com.emanuelef.remote_capture/.activities.CaptureCtrl \
    -e action stop
```

- Runs in **VPN mode** (no root required)
- PCAP file saved to device's `Download/PCAPdroid/` folder, then pulled via ADB
- API key optional but recommended to skip user consent dialog

### Video Recording

Uses Appium's built-in screen recording (not Android `screenrecord`):

```python
# Start recording (returns immediately)
driver.start_recording_screen()

# Stop and get base64 video data
video_base64 = driver.stop_recording_screen()

# Decode and save to file
video_bytes = base64.b64decode(video_base64)
with open(output_path, 'wb') as f:
    f.write(video_bytes)
```

- No 3-minute limit (Appium handles segmentation internally)
- Video saved to session folder after crawl ends

### MobSF Static Analysis

- Triggered after crawl (or on-demand for past runs)
- APK extracted from device via `adb pull`
- Uploaded to MobSF server via REST API
- Results (PDF + JSON) saved to `mobsf_scan_results/` folder
- Errors (split APKs, system apps) logged but do not fail crawl

---

## User Interfaces

The tool provides **two interfaces** sharing identical core logic:

| Interface | Technology | Entry Point | Use Case |
|-----------|------------|-------------|----------|
| **GUI** | PySide6 (Qt) | `run_ui.py` | Interactive use, real-time monitoring, settings management |
| **CLI** | Click | `run_cli.py` | Automation, scripting, CI integration |

Both interfaces communicate with the core via `CrawlerEventListener` protocol:
- **GUI**: Receives events via a Qt signal adapter (core does not import Qt directly)
- **CLI**: Structured JSON events to **stdout** (pipeable); human-readable logs to **stderr**

---

## Crawl State Machine

The crawler operates as an explicit state machine:

```
UNINITIALIZED → INITIALIZING → RUNNING ⇄ PAUSED_MANUAL → STOPPING → STOPPED
                                   ↓
                                 ERROR
```

| State | Description |
|-------|-------------|
| `UNINITIALIZED` | Initial state before any setup |
| `INITIALIZING` | Setting up Appium session, launching app |
| `RUNNING` | Actively crawling |
| `PAUSED_MANUAL` | User-initiated pause; can resume |
| `STOPPING` | Graceful shutdown in progress |
| `STOPPED` | Crawl complete or terminated |
| `ERROR` | Unrecoverable error; crawl halted |

### Crawl Control

| Action | Behavior |
|--------|----------|
| **Start** | Validate pre-crawl requirements → initialize → begin loop |
| **Pause** | Set pause flag; loop waits after current step completes |
| **Resume** | Clear pause flag; loop continues |
| **Stop** | Set shutdown flag; graceful cleanup and report generation |

**Note**: Pause/resume only works while the process is alive. If the host crashes, the run is marked as `ERROR` and cannot be resumed.

---

## Screen State Management

### Screen Representation

Each discovered screen is represented as:

```python
@dataclass
class ScreenRepresentation:
    id: int                          # Database ID
    composite_hash: str              # Unique identifier (activity + visual hash)
    visual_hash: str                 # Perceptual hash of screenshot
    screenshot_path: Optional[str]   # File path
    activity_name: Optional[str]     # Android activity name
```

### Visual Similarity Detection

Screens are deduplicated using perceptual hashing:

```python
VISUAL_SIMILARITY_THRESHOLD = 5  # Hamming distance (fixed, not configurable)

# If hash distance <= threshold, screens are considered the same
if visual_hash_distance(new_hash, existing_hash) <= threshold:
    # Reuse existing screen record
```

### Visit Tracking

Per-crawl tracking maintained:
- `visit_counts: Dict[screen_hash, int]` — times each screen visited (for stuck detection)

---

## Exploration Journal

AI receives a rolling journal (last 15 entries) for context, **derived at runtime from `step_logs`**. This is the **only** history sent to the AI (no separate `action_history` field):

```python
@dataclass
class JournalEntry:
    step: int
    screen: str          # Activity name or hash
    action: str          # Action description
    outcome: str         # "Success" / "Failed: reason"
    reasoning: str       # From ai_suggestion_json

def get_exploration_journal(run_id: int, limit: int = 15) -> List[JournalEntry]:
    """Query last N steps from step_logs; no separate storage needed."""
    rows = db.query("""
        SELECT sl.step_number, sl.action_description, sl.execution_success,
               sl.error_message, sl.ai_suggestion_json, s.activity_name
        FROM step_logs sl
        LEFT JOIN screens s ON sl.to_screen_id = s.id
        WHERE sl.run_id = ?
        ORDER BY sl.step_number DESC LIMIT ?
    """, (run_id, limit))
    return [JournalEntry(...) for r in reversed(rows)]
```

This avoids redundant storage—`step_logs` is the single source of truth for action history.

---

## Runtime Statistics

Comprehensive metrics tracked during each crawl session for maximum data collection:

### Crawl Progress
| Metric | Description |
|--------|-------------|
| `total_steps` | Total steps executed |
| `successful_steps` | Steps with successful action execution |
| `failed_steps` | Steps where action failed |
| `crawl_duration_seconds` | Total elapsed time |
| `avg_step_duration_ms` | Average time per step (capture + AI + execute) |

### Screen Discovery
| Metric | Description |
|--------|-------------|
| `unique_screens_visited` | Distinct screens discovered |
| `total_screen_visits` | Total screen visits (including revisits) |
| `screens_per_minute` | Discovery rate |
| `deepest_navigation_depth` | Max steps from launch to a screen |
| `most_visited_screen_id` | Screen with highest visit count |
| `most_visited_screen_count` | Visit count for that screen |

### Action Statistics
| Metric | Description |
|--------|-------------|
| `actions_by_type` | Dict: `{click: N, input: N, scroll_down: N, ...}` |
| `successful_actions_by_type` | Dict: success count per action type |
| `failed_actions_by_type` | Dict: failure count per action type |
| `avg_action_duration_ms` | Average execution time per action |
| `min_action_duration_ms` | Fastest action |
| `max_action_duration_ms` | Slowest action |

### AI Performance
| Metric | Description |
|--------|-------------|
| `total_ai_calls` | Number of AI requests made |
| `avg_ai_response_time_ms` | Average AI latency |
| `min_ai_response_time_ms` | Fastest AI response |
| `max_ai_response_time_ms` | Slowest AI response |
| `ai_timeout_count` | Times AI timed out |
| `ai_error_count` | AI errors (non-timeout) |
| `ai_retry_count` | Retried AI calls |
| `invalid_response_count` | JSON parse / schema failures |

### Multi-Action Batching
| Metric | Description |
|--------|-------------|
| `multi_action_batch_count` | Batches with >1 action |
| `single_action_count` | Batches with exactly 1 action |
| `total_batch_actions` | Total actions across all batches |
| `avg_batch_size` | Average actions per batch |
| `max_batch_size` | Largest batch executed |
| `batch_success_rate` | % of batches fully successful |

### Error & Recovery
| Metric | Description |
|--------|-------------|
| `stuck_detection_count` | Times loop/stuck detected |
| `stuck_recovery_success` | Times AI escaped stuck state |
| `app_crash_count` | App crashes requiring relaunch |
| `app_relaunch_count` | Total app relaunches |
| `context_loss_count` | Times app left target package |
| `context_recovery_count` | Successful returns to target app |
| `invalid_bbox_count` | Bounding boxes outside screen |

### Device & Session
| Metric | Description |
|--------|-------------|
| `device_id` | Target device identifier |
| `device_model` | Device model (if detectable) |
| `android_version` | Android OS version |
| `screen_resolution` | Device screen dimensions |
| `app_package` | Target app package |
| `app_version` | Target app version (if detectable) |
| `session_start_time` | Crawl start timestamp |
| `session_end_time` | Crawl end timestamp |

### Network & Security (from integrations)
| Metric | Description |
|--------|-------------|
| `pcap_file_size_bytes` | Traffic capture file size |
| `pcap_packet_count` | Number of captured packets (if parseable) |
| `mobsf_security_score` | MobSF security score |
| `mobsf_high_issues` | High-severity issues found |
| `mobsf_medium_issues` | Medium-severity issues |
| `mobsf_low_issues` | Low-severity issues |
| `video_file_size_bytes` | Recording file size |
| `video_duration_seconds` | Recording duration |

### Coverage Estimates
| Metric | Description |
|--------|-------------|
| `screens_with_unexplored_elements` | Screens where not all visible elements were interacted with |
| `unique_activities_visited` | Distinct Android activities |
| `transition_count` | Total screen-to-screen transitions |
| `unique_transitions` | Distinct transition paths |
| `navigation_graph_edges` | Edges in screen transition graph |

---

## Allowed External Packages

A configurable whitelist of packages the AI may navigate to without triggering context-loss recovery:

| Example Package | Purpose |
|-----------------|---------|
| `com.android.chrome` | OAuth flows, web verification and other popular browsers |
| `com.google.android.gms` | Google Sign-In |

When current package is in the allowed list, the crawler continues without pressing back or relaunching the target app.

---

## Supported Actions

| Action | Description | Requires `target_bounding_box` | Requires `input_text` |
|--------|-------------|-------------------------------|----------------------|
| `click` | Tap at coordinates | Yes | No |
| `input` | Type text into field (taps first, then types) | Yes | Yes |
| `long_press` | Long press at coordinates | Yes | No |
| `scroll_up` | Scroll up from screen center | No | No |
| `scroll_down` | Scroll down from screen center | No | No |
| `swipe_left` | Swipe left (e.g., carousels, tabs) | No | No |
| `swipe_right` | Swipe right | No | No |
| `back` | Press Android back button | No | No |

---

## Model Adapter Interface

Abstract interface for AI provider integration:

```python
class ModelAdapter(ABC):
    """Abstract base class for AI model adapters."""
    
    @abstractmethod
    def initialize(self, model_config: Dict[str, Any], safety_settings: Optional[Dict] = None) -> None:
        """Initialize the model with the provided configuration."""
        pass
    
    @abstractmethod
    def generate_response(self, 
                          prompt: str, 
                          image: Optional[Image.Image] = None,
                          **kwargs) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a response from the model.
        
        Args:
            prompt: Text prompt to send
            image: Optional PIL Image for vision models
            **kwargs: Provider-specific options
            
        Returns:
            Tuple of (response_text, metadata_dict)
            metadata_dict includes: tokens_used, latency_ms, model_name, etc.
        """
        pass
    
    @property
    @abstractmethod
    def model_info(self) -> Dict[str, Any]:
        """Return information about the model (provider, family, name, vision_capable)."""
        pass
```

Concrete implementations: `GeminiAdapter`, `OpenRouterAdapter`, `OllamaAdapter`.

---

## Storage Architecture

### Overview

| Storage | Database | Purpose |
|---------|----------|---------|
| **Crawl data** | `crawler.db` (SQLite) | Runs, screens, steps, transitions, stats, AI interactions |
| **User config** | `user_config.db` (SQLite) | Settings, API keys (encrypted), model selection |
| **Binary files** | File system | Screenshots, video, PCAP, MobSF reports, logs |

### File System Layout

```
{app_root}/
├── crawler.db                      # Crawl data (runs, screens, steps, etc.)
├── user_config.db                  # User settings and encrypted secrets
└── output_data/
    └── {device_id}_{app_package}_{DDMM_HHMM}/   # e.g., emulator-5554_com.example.app_1001_1430
        ├── screenshots/
        │   ├── step_001.png
        │   └── ...
        ├── logs/
        │   └── crawler.log
        ├── video/
        │   └── crawl_recording.mp4
        ├── traffic_captures/
        │   └── session_capture.pcap
        ├── extracted_apk/
        │   └── {package}.apk
        └── mobsf_scan_results/
            ├── {package}_security_report.pdf
            └── {package}_security_report.json
```

### Why Two Databases

| Database | Reason |
|----------|--------|
| `crawler.db` | Crawl-specific data; can grow large; tied to output_data sessions |
| `user_config.db` | User preferences; small; easy to backup/reset independently; survives crawl data deletion |

### Stale Run Cleanup

On application startup, check for runs with `status=RUNNING` that have no active process:

1. **Attempt recovery**:
   - Stop Appium video recording if possible; save partial video
   - Send PCAPdroid stop intent; pull partial PCAP from device
2. **Mark as ERROR**: Update run status to `ERROR` with cleanup timestamp
3. **Log**: Record recovery attempt results in `crawler.log`

### Run Deletion

Users can delete old runs via UI/CLI. Deletion is **cascading**:

1. Delete row from `runs` table (cascades to `step_logs`, `transitions`, `run_stats`, `ai_interactions`)
2. Delete associated session folder (`output_data/{device_id}_{app_package}_{timestamp}/`)
3. Orphaned `screens` records are retained (may be referenced by other runs)

---

## Database Schema

### Database: `crawler.db`

**`runs`** — Crawl session metadata
```sql
CREATE TABLE runs (
    id INTEGER PRIMARY KEY,
    device_id TEXT NOT NULL,
    app_package TEXT NOT NULL,
    start_activity TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT,
    status TEXT NOT NULL,           -- RUNNING, STOPPED, ERROR
    ai_provider TEXT,               -- gemini, openrouter, ollama
    ai_model TEXT,                  -- model name used
    total_steps INTEGER DEFAULT 0,
    unique_screens INTEGER DEFAULT 0
);
```

**`screens`** — Discovered screen states
```sql
CREATE TABLE screens (
    id INTEGER PRIMARY KEY,
    composite_hash TEXT UNIQUE NOT NULL,
    visual_hash TEXT NOT NULL,
    screenshot_path TEXT,
    activity_name TEXT,
    first_seen_run_id INTEGER NOT NULL,
    first_seen_step INTEGER NOT NULL,
    FOREIGN KEY (first_seen_run_id) REFERENCES runs(id)
);
```

**`step_logs`** — Per-step action history
```sql
CREATE TABLE step_logs (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL,
    step_number INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    from_screen_id INTEGER,
    to_screen_id INTEGER,
    action_type TEXT NOT NULL,      -- click, input, scroll_down, etc.
    action_description TEXT,        -- human-readable
    target_bbox_json TEXT,          -- {"top_left": [...], "bottom_right": [...]}
    input_text TEXT,                -- for input actions
    execution_success BOOLEAN NOT NULL,
    error_message TEXT,
    action_duration_ms REAL,
    ai_response_time_ms REAL,
    ai_reasoning TEXT,              -- AI's reasoning for this action
    FOREIGN KEY (run_id) REFERENCES runs(id),
    FOREIGN KEY (from_screen_id) REFERENCES screens(id),
    FOREIGN KEY (to_screen_id) REFERENCES screens(id)
);
```

**`transitions`** — Screen-to-screen navigation graph (per run)
```sql
CREATE TABLE transitions (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL,
    from_screen_id INTEGER NOT NULL,
    to_screen_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    count INTEGER DEFAULT 1,
    FOREIGN KEY (run_id) REFERENCES runs(id),
    FOREIGN KEY (from_screen_id) REFERENCES screens(id),
    FOREIGN KEY (to_screen_id) REFERENCES screens(id),
    UNIQUE(run_id, from_screen_id, to_screen_id, action_type)
);
```

**`run_stats`** — Comprehensive statistics per crawl session
```sql
CREATE TABLE run_stats (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL UNIQUE,
    
    -- Crawl Progress
    total_steps INTEGER DEFAULT 0,
    successful_steps INTEGER DEFAULT 0,
    failed_steps INTEGER DEFAULT 0,
    crawl_duration_seconds REAL,
    avg_step_duration_ms REAL,
    
    -- Screen Discovery
    unique_screens_visited INTEGER DEFAULT 0,
    total_screen_visits INTEGER DEFAULT 0,
    deepest_navigation_depth INTEGER DEFAULT 0,
    most_visited_screen_id INTEGER,
    most_visited_screen_count INTEGER DEFAULT 0,
    unique_activities_visited INTEGER DEFAULT 0,
    
    -- Action Statistics (JSON for flexibility)
    actions_by_type_json TEXT,           -- {"click": 50, "input": 10, ...}
    successful_actions_by_type_json TEXT,
    failed_actions_by_type_json TEXT,
    avg_action_duration_ms REAL,
    min_action_duration_ms REAL,
    max_action_duration_ms REAL,
    
    -- AI Performance
    total_ai_calls INTEGER DEFAULT 0,
    avg_ai_response_time_ms REAL,
    min_ai_response_time_ms REAL,
    max_ai_response_time_ms REAL,
    ai_timeout_count INTEGER DEFAULT 0,
    ai_error_count INTEGER DEFAULT 0,
    ai_retry_count INTEGER DEFAULT 0,
    invalid_response_count INTEGER DEFAULT 0,
    total_ai_tokens_used INTEGER,
    
    -- Multi-Action Batching
    multi_action_batch_count INTEGER DEFAULT 0,
    single_action_count INTEGER DEFAULT 0,
    total_batch_actions INTEGER DEFAULT 0,
    avg_batch_size REAL,
    max_batch_size INTEGER DEFAULT 0,
    
    -- Error & Recovery
    stuck_detection_count INTEGER DEFAULT 0,
    stuck_recovery_success INTEGER DEFAULT 0,
    app_crash_count INTEGER DEFAULT 0,
    app_relaunch_count INTEGER DEFAULT 0,
    context_loss_count INTEGER DEFAULT 0,
    context_recovery_count INTEGER DEFAULT 0,
    invalid_bbox_count INTEGER DEFAULT 0,
    
    -- Device & App Info
    device_model TEXT,
    android_version TEXT,
    screen_width INTEGER,
    screen_height INTEGER,
    app_version TEXT,
    
    -- Network & Security
    pcap_file_size_bytes INTEGER,
    pcap_packet_count INTEGER,
    mobsf_security_score REAL,
    mobsf_high_issues INTEGER DEFAULT 0,
    mobsf_medium_issues INTEGER DEFAULT 0,
    mobsf_low_issues INTEGER DEFAULT 0,
    video_file_size_bytes INTEGER,
    video_duration_seconds REAL,
    
    -- Coverage
    transition_count INTEGER DEFAULT 0,
    unique_transitions INTEGER DEFAULT 0,
    
    FOREIGN KEY (run_id) REFERENCES runs(id),
    FOREIGN KEY (most_visited_screen_id) REFERENCES screens(id)
);
```

### ai_interactions (AI Request/Response Logging)
```sql
CREATE TABLE ai_interactions (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL,
    step_number INTEGER NOT NULL,
    timestamp TEXT NOT NULL,               -- ISO 8601
    
    -- Request Details
    request_json TEXT,                     -- Full request payload
    screenshot_path TEXT,                  -- Path to screenshot sent
    
    -- Response Details
    response_raw TEXT,                     -- Raw AI response
    response_parsed_json TEXT,             -- Parsed/validated JSON
    
    -- Performance Metrics
    tokens_input INTEGER,
    tokens_output INTEGER,
    latency_ms REAL,
    
    -- Status
    success BOOLEAN NOT NULL DEFAULT 0,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    FOREIGN KEY (run_id) REFERENCES runs(id)
);
```

---

## User Configuration Database (user_config.db)

Separate database for user preferences and secrets, kept distinct from crawl data.

### user_config (Key-Value Settings)
```sql
CREATE TABLE user_config (
    key TEXT PRIMARY KEY,
    value TEXT,
    value_type TEXT NOT NULL,              -- 'string', 'int', 'float', 'bool', 'json'
    updated_at TEXT NOT NULL               -- ISO 8601
);
```

### secrets (Encrypted API Keys)
```sql
CREATE TABLE secrets (
    key TEXT PRIMARY KEY,                  -- e.g., 'gemini_api_key', 'openrouter_api_key'
    encrypted_value BLOB NOT NULL,
    updated_at TEXT NOT NULL               -- ISO 8601
);
```

---

## Indexes

### crawler.db Indexes
```sql
CREATE INDEX idx_step_logs_run ON step_logs(run_id, step_number);
CREATE INDEX idx_screens_hash ON screens(composite_hash);
CREATE INDEX idx_transitions_run ON transitions(run_id);
CREATE INDEX idx_run_stats_run ON run_stats(run_id);
CREATE INDEX idx_ai_interactions_run ON ai_interactions(run_id, step_number);
```

### user_config.db Indexes
```sql
CREATE INDEX idx_user_config_updated ON user_config(updated_at);
```

---

## Logging Infrastructure

### Multi-Sink Architecture

```
LoggingService
├── ConsoleSink      → stderr (human-readable, level-filtered)
├── JSONEventSink    → stdout (structured events for CLI piping / GUI IPC)
├── FileSink         → crawler.log (all levels, single rotated file)
└── DatabaseSink     → step_logs table (on step completion only)
```

### Log Levels

| Level | ConsoleSink (stderr) | FileSink | DatabaseSink |
|-------|----------------------|----------|--------------|
| DEBUG | No | Yes | No |
| INFO | Yes | Yes | No |
| WARNING | Yes | Yes | No |
| ERROR | Yes | Yes | Yes (`error_message`) |
| ACTION | Yes | Yes | Yes (full step record) |

### Log Files

| File | Contents |
|------|----------|
| `crawler.log` | All activity: state changes, actions, AI prompts/responses, errors (single rotated file) |

**Note**: AI interactions are logged at DEBUG level in `crawler.log`. No separate files—single log simplifies debugging.

---

## Output Folder Structure

Each crawl session produces:

```
output_data/{device_id}_{app_package}_{DDMM_HHMM}/
├── screenshots/
│   ├── step_001.png
│   ├── step_002.png
│   └── ...
├── logs/
│   └── crawler.log
├── video/
│   └── crawl_recording.mp4
├── traffic_captures/
│   └── session_capture.pcap
├── extracted_apk/
│   └── {package}.apk
└── mobsf_scan_results/
    ├── {package}_security_report.pdf
    └── {package}_security_report.json
```

---

## Pre-Crawl Validation

Before starting a crawl, the following checks are performed:

| Check | Required | Recovery |
|-------|----------|----------|
| Appium server reachable (`/status`) | Yes | Block start; show setup instructions |
| Device connected via ADB | Yes | Block start; prompt to connect device |
| Target app selected | Yes | Block start; prompt to select app |
| AI model selected (vision-capable) | Yes | Block start; prompt to select model |
| API key present (for cloud providers) | Yes | Block start; prompt to configure |
| MobSF server reachable | No (optional) | Warn user; allow start without static analysis |
| PCAPdroid installed on device | No (optional) | Warn user; allow start without traffic capture |
| Video recording available | No (optional) | Warn user; allow start without video |

---

## Configuration Precedence

Configuration values are resolved in this order (highest priority first):

1. **User storage (SQLite)** — Persistent settings from UI/CLI
2. **Environment variables** — Override for CI/automation
3. **Module defaults** — Fallback values in code

Example:
```python
# Resolved value for AI_PROVIDER:
# 1. Check user_config.db for AI_PROVIDER
# 2. Check os.environ["AI_PROVIDER"]
# 3. Fall back to "gemini" (default)
```

---

> If any requirement above is unclear or needs adjustment, please clarify before implementation.
