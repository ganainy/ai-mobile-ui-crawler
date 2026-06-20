---
title: Input-text failure analysis
date: 2026-06-07
context: gsd-explore
---

- Current typing failures are consistent with focus races, layout shifts, and direct ADB text injection without field verification.
- `type_text` taps the field and waits briefly, but `type_secret` skips `clear` and types straight into the currently focused element.
- `AndroidDriver.input_text()` uses `adb shell input text`, and its `clear=True` path is a fixed backspace heuristic.
- The strongest external pattern is to keep text entry stateful: verify focus, clear explicitly, then type.
