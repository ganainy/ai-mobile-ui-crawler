# Contract: AppSwitcher

**Module**: `mobile_crawler.infrastructure.app_switcher`  
**Purpose**: Utility for switching between Android apps during crawl execution

## Interface

### `class AppSwitcher`

Manages app switching operations.

#### Constructor

```python
def __init__(self, appium_driver: AppiumDriver) -> None
```

**Parameters**:
- `appium_driver`: Appium driver for device interaction

---

### Methods

#### `switch_to_app(package_name: str, timeout: int = 10) -> bool`

Switches to the specified app by package name.

**Parameters**:
- `package_name`: Android package name (e.g., "com.google.android.gm")
- `timeout`: Maximum time to wait for app switch in seconds (default: 10)

**Returns**: `True` if switch successful, `False` otherwise

**Behavior**:
1. Calls `driver.activate_app(package_name)`
2. Waits for app to come to foreground
3. Verifies switch by checking `driver.current_package`
4. Returns True if package matches, False otherwise

**Raises**:
- `AppSwitchError`: If app switch fails after timeout

---

#### `switch_to_gmail() -> bool`

Convenience method to switch to Gmail app.

**Returns**: `True` if switch successful, `False` otherwise

**Behavior**:
- Calls `switch_to_app("com.google.android.gm")`

---

#### `switch_back_to_target(target_package: str) -> bool`

Switches back to the target app after Gmail interaction.

**Parameters**:
- `target_package`: Original target app package name

**Returns**: `True` if switch successful, `False` otherwise

**Behavior**:
- Calls `switch_to_app(target_package)`
- Used after Gmail interaction to return to target app

---

#### `get_current_package() -> Optional[str]`

Gets the currently active app package.

**Returns**: Package name if available, `None` otherwise

**Behavior**:
- Returns `driver.current_package`
- Used to verify app state

---

#### `is_app_foreground(package_name: str) -> bool`

Checks if specified app is in foreground.

**Parameters**:
- `package_name`: Android package name

**Returns**: `True` if app is foreground, `False` otherwise

**Behavior**:
- Compares `driver.current_package` with `package_name`
- Used to verify app state without switching

---

## Error Types

### `AppSwitchError`

Raised when app switching fails.

```python
class AppSwitchError(Exception):
    """Raised when app switch operation fails."""
    pass
```

---

## Usage Example

```python
# Initialize
app_switcher = AppSwitcher(appium_driver)

# Get current app
current = app_switcher.get_current_package()
print(f"Currently in: {current}")

# Switch to Gmail
if app_switcher.switch_to_gmail():
    # Interact with Gmail
    # ...
    
    # Switch back to target app
    app_switcher.switch_back_to_target("com.example.app")
else:
    raise AppSwitchError("Failed to switch to Gmail")

# Verify app state
if app_switcher.is_app_foreground("com.example.app"):
    print("Successfully returned to target app")
```

---

## Known Package Names

**Gmail**: `com.google.android.gm`

**Common Patterns**:
- Package names follow reverse domain notation
- Can be verified via `adb shell pm list packages`
- App must be installed on device

---

## Implementation Notes

- Uses Appium's `activate_app()` method
- Waits 1-2 seconds after switch for app to load
- Verifies switch by checking `current_package`
- Handles cases where app is not installed
- Logs all switch operations for debugging
