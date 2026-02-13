# Verification CLI Contract

**Script**: `run_verification.py` (or similar entry point)

## Arguments

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `--package` | string | No | `com.example.flutter_application_1` | The package name of the test app |
| `--activity` | string | No | (Auto-detect) | The main launch activity |
| `--test-type` | string | No | `all` | Filter tests: `tap`, `input`, `swipe`, `all` |
| `--headless` | flag | No | `False` | Run without GUI/Console emphasis (standard logging) |

## Output (stdout)

The script MUST output JSON on the last line regarding the overall pass/fail status for programmatic parsing, or standard human-readable text logs.

**Example JSON Output (last line)**:
```json
{
  "status": "PASS",
  "passed": 5,
  "failed": 0,
  "duration": 12.5
}
```
