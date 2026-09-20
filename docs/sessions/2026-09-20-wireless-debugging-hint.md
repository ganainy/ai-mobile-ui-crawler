---
author: claude
---
# Wireless debugging device not listed

- Report: phone connected via wireless debugging, app shows "No Devices Found".
- Finding: `adb devices -l` and `adb mdns services` both returned nothing, so the phone was never paired/connected to the adb server. `DeviceDetection` parses wireless ids fine and only filters on status `device`. PATH has two adbs (Android SDK platform-tools first, scrcpy's bundled one second); a version mismatch can make servers restart and drop connections.
- Change: `ui/widgets/device_selector.py` dialog now lists USB and wireless (`adb pair`, `adb connect`) steps.
- Not done: no in-app pair/connect button; not seen in the real GUI.
