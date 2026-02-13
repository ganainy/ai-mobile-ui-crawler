# Research Plan: Image-Only Crawler

## Overview

The goal is to eliminate non-visual methods of interaction (XML/PageSource/OCR).

### Research Tasks

- [x] **Task 1: Verify Text Input Strategy**
  - **Question**: How to send text input reliably without `find_element` or XML access?
  - **Context**: `ActionExecutor.input` uses `find_element_by_xpath("//*").send_keys(text)`. This queries the DOM.
  - **Approaches**:
    - `adb shell input text "..."` (handles basic chars, need to escape spaces/symbols).
    - `driver.press_keycode` (slow for long text).
    - `driver.get_driver().execute_script("mobile: type", ...)` (Appium specific features?).
    - Clipboard + Paste (adb input keyevent 279).
  - **Goal**: Find a robust method that doesn't query UI hierarchy.

- [x] **Task 2: Verify `AppiumDriver` Cleanliness**
  - **Question**: Does `AppiumDriver` rely on page source anywhere else?
  - **Context**: `_get_launch_activity` uses ADB (safe). `is_connected` uses `current_activity` (safe).
  - **Goal**: Confirm no hidden XML dependencies.

- [x] **Task 3: Confirm VLM Coordinate Capability**
  - **Context**: `AIInteractionService` builds prompts. The prompt must explicitly ask for normalized coordinates.
  - **Goal**: Review `prompt_builder.py` (which I haven't seen yet) to ensure it handles JSON output with coordinates correctly.

- [x] **Task 4: Identify Legacy OCR Usage**
  - **Context**: User mentioned removing code "to do with XML or OCR".
  - **Goal**: Verify if `tesseract` or `easyocr` are imported anywhere and need removal.

## Findings

### Text Input Strategy
**Decision**: Use `adb shell input text` for fast input or `driver.press_keycode` for specific keys. If special chars are an issue, Clipboard + Paste is a good fallback. 
**Detailed Plan**:
1. Tap on the coordinate (handled by VLM).
2. Wait a moment for focus.
3. Run `adb shell input text <escaped_text>`.
4. If that fails (e.g. non-ASCII), consider `adb shell input keyevent` loop or Clipboard override.
**Constraint Check**: This avoids `driver.page_source` and `find_element`.

### Appium Driver
**Decision**: `AppiumDriver` seems largely clean. `_get_launch_activity` uses ADB. `current_package` / `current_activity` are metadata, not DOM traversal.
**Action**: Remove any comments or unused methods that reference `page_source` if found.

### VLM Coordinates
**Decision**: `AIInteractionService` already processes `target_bounding_box` in `AIAction`. The logic in `crawler_loop.py` scales it back.
**Action**: Ensure `PromptBuilder` instructs the model to return coordinates relative to the resolution provided in the screenshot.

### Legacy OCR
**Decision**: I previously searched for "ocr" and "tesseract" and found nothing (except in requirements maybe). I will double check `requirements.txt` content (previously failed to read).
**Action**: If `requirements.txt` has `pytesseract` or `easyocr`, remove them.

