# Vendored scrcpy server

`scrcpy-server-v3.3.4.jar` is the unmodified server from scrcpy v3.3.4
(https://github.com/Genymobile/scrcpy, Apache License 2.0, Copyright Genymobile).
It runs on the device to provide the Live Feed; see docs/adr/0004.

To upgrade: replace the jar and update `SERVER_VERSION` in
`src/mobile_crawler/domain/scrcpy_stream.py` together.
