# Android Input Focus, Clearing, and Escaping Fixes

Plan to verify and formalize fixes for input focus race conditions, keyevent clearing limitations, and shell character escaping in the Android driver and ADB action executor.

---

## Overview

During automated device exploration, input tasks frequently failed or registered incomplete text. The diagnostics identified four key issues:
1. **Focus Race Condition**: In `actions.py`'s `type_text`, the tap occurred and text input was initiated immediately before the keyboard focus or layout scrolling animation settled.
2. **Broken Selection Keyevents**: Simulated select-all sequences using modifier keys (`KEYCODE_CTRL_A`) failed over ADB shell, leading to incomplete/uncleared text fields.
3. **Escaping Limitations**: Raw space characters and shell-sensitive characters like `$`, `\`, and `` ` `` broke input sequences.
4. **Keyboard Layout Shifts**: Misaligned taps due to layout shifts caused text to fall back into previously focused fields.

This plan outlines the testing, verification, and formal documentation of the fixes addressing these diagnostics.

---

## Project Type
- **Type**: MOBILE
- **Platform**: Android
- **Component**: Device Driver / Action Executor

---

## Success Criteria
- [ ] 0.5s delay settles input focus after tap, preventing text drops on layout transitions.
- [ ] Text field clearing reliably moves cursor to end and sends 100 DEL events in <50ms.
- [ ] Safe escaping maps spaces to `%s` and escapes `\`, `"`, `$`, and `` ` ``.
- [ ] All unit tests pass successfully.

---

## Open Questions

> [!IMPORTANT]
> **1. Configurable Focus Delay**
> Should the 0.5-second delay introduced in `actions.py` be configurable via `config.yaml`? Slower emulators or older devices might require longer focus times (e.g. 0.8s or 1s).
>
> **2. iOS Driver Alignment**
> Does the iOS driver/executor experience similar text clearing or focus latency problems, or is this currently scoped strictly to Android and ADB?
>
> **3. Additional Escaping Characters**
> Are there other special shell characters we should proactively escape (e.g., `&`, `|`, `;`, `<`, `>`) in the input sequence, or is the current subset (`\`, `"`, `$`, `` ` ``) sufficient?

---

## Proposed Changes

### Android Driver & Executor

#### [MODIFY] [actions.py](file:///e:/VS-projects/mobile-crawler/src/mobile_crawler/domain/crawler_agent/agent/utils/actions.py)
- Introduce a 0.5-second focus delay in `type_text` immediately after tapping the text input coordinates.

#### [MODIFY] [android.py](file:///e:/VS-projects/mobile-crawler/src/mobile_crawler/domain/crawler_agent/tools/driver/android.py)
- Replace selection-based clearing with chained cursor end (`123`) and 100 backspaces (`67`) keyevent shell command.
- Implement robust character escaping (`\`, `"`, `$`, `` ` `` and mapping spaces to `%s`).

#### [MODIFY] [adb_action_executor.py](file:///e:/VS-projects/mobile-crawler/src/mobile_crawler/domain/adb_action_executor.py)
- Align `ADBActionExecutor.input` with the same chained keyevent clear logic and robust character escaping.

### Verification & Testing

#### [NEW] [test_android_driver_input.py](file:///e:/VS-projects/mobile-crawler/tests/domain/test_android_driver_input.py)
- Verify `input_text` behaves correctly without clearing.
- Verify `input_text` issues chained keyevents when `clear=True`.
- Verify escaping of backslashes, double quotes, dollar signs, backticks, and spaces.

---

## Verification Plan

### Automated Tests
Run unit tests for both drivers:
```powershell
python -m pytest tests/domain/test_android_driver_input.py
python -m pytest tests/domain/test_adb_action_executor.py
python -m pytest tests/domain/test_crawler_agent_service.py
```

### Manual Verification
- Deploy to a device/emulator.
- Inspect execution traces to verify:
  1. Keyevents are sent correctly as a single chained shell command.
  2. Input field is empty before text entry.
  3. No dropped characters on fast transitions.

---

## ✅ PHASE X: Final Verification
- [ ] Code compiles and builds cleanly
- [ ] All unit and integration tests pass
- [ ] No purple/violet hex codes in changes
- [ ] Socratic Gate was respected
