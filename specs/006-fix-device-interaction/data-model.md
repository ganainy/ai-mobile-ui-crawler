# Data Model: Device Interaction Verification

## Entities

### `VerificationCase`
Represents a single test scenario to run on the device.

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique name of the test case (e.g., "test_tap_coordinates") |
| `description` | string | Human readable description of what is tested |
| `action_type` | enum | `TAP`, `INPUT`, `SWIPE`, `NAVIGATE` |
| `target_element` | dictionary | Locator strategy (e.g., `{'text': 'Sign In'}`) |
| `expected_result` | dictionary | Condition to verify success (e.g., `{'text_visible': 'Login Success'}`) |

### `VerificationReport`
The output of a verification run.

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | datetime | When the run started |
| `device_info` | dictionary | Connected device metadata |
| `results` | list[`TestResult`] | List of individual test outcomes |
| `summary` | string | Overall Pass/Fail status |

### `TestResult`
| Field | Type | Description |
|-------|------|-------------|
| `case_name` | string | Reference to VerificationCase |
| `status` | enum | `PASS`, `FAIL`, `ERROR`, `SKIPPED` |
| `duration_ms` | int | Time taken to execute |
| `error_message` | string | Stack trace or failure reason (if failed) |

## State Management

The verification suite does not traverse the complex `ScreenState` graph of the main crawler. It assumes a linear, deterministic flow:
`Start` -> `Sign Up Screen` -> `Sign In Screen` -> `Success Screen`.
