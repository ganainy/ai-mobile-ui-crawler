---
updated: 2026-09-27
---
# Decrypting HTTPS on a rooted emulator

Why: on a normal phone the pcap stays TLS-encrypted (apps ignore user CAs, Google hosts pin certificates). A rooted emulator lets you put the mitm CA in the **system** store. See issue #31. Untested end to end; adjust as you learn.

## Which emulator

Android Studio AVD, **Pixel 6 (or "Medium Phone"), API 33, "Google APIs" x86_64 image**.

- **Not "Google Play"**: Play images cannot be rooted (`adb root` is refused). Your existing `Medium_Phone` AVD (API 37, Play Store, 16 KB pages) is one of these, so it will not work.
- **API 33, not 34+**: up to API 33 the system CA store can be made writable with `-writable-system`. From API 34 the CAs live in the Conscrypt APEX and need a fiddly overlay.
- "Google APIs" still ships Google Play services, so Google sign-in works. Add a Google account under Settings > Passwords & accounts. Sideload the app (no Play Store): the run already saves APKs in `apks/`, install with `adb install-multiple <run>/apks/*.apk`.

## One-time setup

1. Android Studio > Tools > SDK Manager > SDK Platforms > tick **Android 13 (API 33)** > Show Package Details > **Google APIs Intel x86_64 Atom System Image**. Apply.
2. Device Manager > Create Virtual Device > Pixel 6 > select that image > name it `tls33` > Finish.
3. Start it writable from a terminal (the flag only works from the command line):
   ```
   %LOCALAPPDATA%\Android\Sdk\emulator\emulator.exe -avd tls33 -writable-system -no-snapshot
   ```
4. In a second terminal (other phones unplugged, or add `-s emulator-5554` to every adb command):
   ```
   adb root
   adb disable-verity
   adb reboot
   ```
   Wait for boot, then `adb root` and `adb remount`. If remount fails, restart the emulator with the step 3 command.
5. Install PCAPdroid and its mitm add-on on the emulator (from F-Droid or GitHub releases; the emulator has no Play Store, so `adb install` the APKs). Open PCAPdroid > Settings > enable **TLS decryption** > install the add-on when prompted, and note the CA it generates.
6. Export PCAPdroid's CA (Settings > TLS decryption > Export CA certificate, or `adb pull` it). Convert it to the system-store name and push it:
   ```
   openssl x509 -inform PEM -subject_hash_old -in ca.pem | head -1     # prints e.g. 0a1b2c3d
   copy ca.pem 0a1b2c3d.0
   adb push 0a1b2c3d.0 /system/etc/security/cacerts/
   adb shell chmod 644 /system/etc/security/cacerts/0a1b2c3d.0
   adb reboot
   ```
7. Add a Google account, install Flow (`adb install-multiple`), open PCAPdroid once and accept the VPN consent.

## Run a crawl

```
adb devices                      # note emulator-5554
.venv312/Scripts/python.exe -m mobile_crawler.cli.main crawl --help   # then pass the emulator device id
```
Keep `pcapdroid_tls_decryption` true (the GUI sets it when traffic capture is on). Also set the PCAPdroid API key as for a phone, and turn on PCAPdroid's **Block QUIC** so HTTP/3 falls back to TCP.

## If it still doesn't decrypt

- Google hosts pin their certificates: run Frida server on the emulator (`adb root`, push `frida-server` matching the ABI, run it) and load a universal pinning-bypass script.
- Flow or Google sign-in may refuse an emulator (integrity checks). Then the emulator route is closed for that app.
- Check the pcap: a decrypted capture shows plain HTTP after PCAPdroid's TLS layer; a still-encrypted one shows only SNI hostnames.
