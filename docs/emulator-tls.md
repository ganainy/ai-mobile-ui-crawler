---
updated: 2026-09-27
---
# Decrypting HTTPS on a rooted emulator

Why: on a normal phone the pcap stays TLS-encrypted (apps ignore user-installed CAs, Google hosts pin certificates). A rooted emulator lets you put the mitm CA in the **system** certificate store. Background and open tasks: issue #31.

Steps marked **(done)** were actually run on the user's PC (Windows, PowerShell) on 2026-09-27 and worked. Steps marked **(untested)** have not been tried yet.

## Which emulator

AVD **`tls33`**: Pixel 6, **API 33, "Google APIs" x86_64** image, created with the SDK command-line tools (no Android Studio needed).

- **Not "Google Play"**: Play images cannot be rooted. The old `Medium_Phone` AVD (API 37, Play Store, 16 KB pages) is one of these and will not work.
- **API 33, not 34+**: up to API 33 the system partition can be made writable with `-writable-system`. From API 34 the CAs live in the Conscrypt APEX and need a fiddly overlay.
- "Google APIs" ships Google Play services (Google sign-in works) but **no Play Store app**, so apps are sideloaded (see "Getting apps onto the emulator").

## One-time setup

All commands are PowerShell. First: `$SDK = "$env:LOCALAPPDATA\Android\Sdk"`.

### 1. Command-line tools (done)

Download "Command line tools only" from https://developer.android.com/studio#command-tools and unzip into `$SDK\cmdline-tools\latest` (rename the inner `cmdline-tools` folder to `latest`, so `latest\bin\sdkmanager.bat` exists).

### 2. Java (done)

The tools' version check rejects Java 26 ("Java version 17 or higher is required": it cannot parse a version string without a dot). Either `$env:SKIP_JDK_VERSION_CHECK = "1"`, or use Android Studio's bundled JDK 21, which is what made `avdmanager` work:

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
```

These settings last for that PowerShell window only.

### 3. System image and AVD (done)

```powershell
& "$SDK\cmdline-tools\latest\bin\sdkmanager.bat" "system-images;android-33;google_apis;x86_64"
1..20 | ForEach-Object { "y" } | & "$SDK\cmdline-tools\latest\bin\sdkmanager.bat" --licenses
& "$SDK\cmdline-tools\latest\bin\avdmanager.bat" create avd -n tls33 -k "system-images;android-33;google_apis;x86_64" -d pixel_6
& "$SDK\emulator\emulator.exe" -list-avds        # should list tls33
```

- `--licenses` asks per license; answer `y` to all (the pipe does that).
- `avdmanager` may print "Could not load devices ... devices.xml" or "AVD already exists" under Java 26. The AVD was still written correctly; check with `-list-avds`.

### 4. Start writable and root it (done)

The `-writable-system` flag only works when starting from the command line, not from a GUI:

```powershell
& "$SDK\emulator\emulator.exe" -avd tls33 -writable-system -no-snapshot
```

In a second window (`-s emulator-5554` because a phone may also be connected):

```powershell
adb -s emulator-5554 root
adb -s emulator-5554 disable-verity
adb -s emulator-5554 reboot
# wait for boot, then:
adb -s emulator-5554 root
adb -s emulator-5554 remount        # "remount succeeded"
```

The emulator must be started with `-writable-system` every time you want to change `/system`. After the CA is installed you can also start it normally.

### 5. PCAPdroid and the mitm add-on (done)

Both from GitHub releases (`emanuele-f/PCAPdroid`, `emanuele-f/PCAPdroid-mitm`). The emulator is x86_64, so take **`PCAPdroid-mitm_v2.4_x86_64.apk`** (not the arm64-v8a one) and the universal PCAPdroid APK.

```powershell
adb -s emulator-5554 install PCAPdroid-mitm_v2.4_x86_64.apk
adb -s emulator-5554 install PCAPdroid_<version>.apk
```

Open PCAPdroid, turn on TLS decryption in its settings (it starts the add-on, which generates a CA).

### 6. Install the mitm CA as a system certificate (done)

With root the CA can be pulled straight from the add-on's data folder:

```powershell
adb -s emulator-5554 shell "find /data/data/com.pcapdroid.mitm -iname '*ca-cert*'"
# /data/data/com.pcapdroid.mitm/files/.mitmproxy/mitmproxy-ca-cert.pem  (also .cer, .p12)

cd $env:USERPROFILE\Downloads
adb -s emulator-5554 pull /data/data/com.pcapdroid.mitm/files/.mitmproxy/mitmproxy-ca-cert.pem ca.pem

$openssl = "C:\Program Files\Git\usr\bin\openssl.exe"      # ships with Git for Windows
$hash = (& $openssl x509 -inform PEM -subject_hash_old -in ca.pem -noout).Trim()
Copy-Item ca.pem "$hash.0"

adb -s emulator-5554 root
adb -s emulator-5554 remount
adb -s emulator-5554 push "$hash.0" /system/etc/security/cacerts/
adb -s emulator-5554 shell chmod 644 /system/etc/security/cacerts/$hash.0
adb -s emulator-5554 reboot
```

Check on the emulator: Settings > Security > Encryption & credentials > Trusted credentials > **System**: "mitmproxy" is listed. (Done: it was.)

## Getting apps onto the emulator

There is no Play Store, so install APKs with `adb`.

- **From a crawl you already ran:** each run saves the target app's APKs in `<run folder>\apks\` (`00_base.apk` plus split files). Install them together:
  ```powershell
  adb -s emulator-5554 install-multiple 00_base.apk 01_split_config.arm64_v8a.apk 02_split_config.xxhdpi.apk
  ```
  **Fails on `tls33`** with `INSTALL_FAILED_NO_MATCHING_ABIS` (res=-113) for Flow: the phone's copy only has an arm64 split, and this "Google APIs" x86_64 image has no ARM translation. You need an **x86_64 (or universal) build** of the app, or add `libndk_translation` to `/system` yourself (root allows it; untested). Apps without native code (e.g. the Portal APK) install fine.
- **From your phone:**
  ```powershell
  adb -s <phone-serial> shell pm path <package>       # lists base + split APK paths
  adb -s <phone-serial> pull <each path>
  adb -s emulator-5554 install-multiple <all the pulled apks>
  ```
- **From the web:** APKMirror / APKPure (verify the source; prefer an x86_64 or "universal" build).
- A Google account is added on the emulator under Settings > Passwords & accounts (needed for Flow's Google sign-in).

## Run a crawl (untested)

```powershell
adb devices                       # note emulator-5554
.venv312\Scripts\python.exe -m mobile_crawler.cli.main crawl --help    # then pass the emulator's device id
```

Keep `pcapdroid_tls_decryption` true (the GUI sets it when traffic capture is on), set the PCAPdroid API key as for a phone, accept the VPN consent once, and turn on PCAPdroid's **Block QUIC** so HTTP/3 falls back to TCP. Whether the crawler's device selector, scrcpy, Portal and screenrecord all work on the emulator is unverified.

## If it still doesn't decrypt

- Google hosts pin their certificates: run Frida server on the emulator (`adb root`, push the `frida-server` matching the ABI, run it) and load a universal pinning-bypass script.
- Flow or Google sign-in may refuse an emulator (integrity checks). Then this route is closed for that app.
- Check the pcap: a decrypted capture shows plain HTTP inside the TLS flows; a still-encrypted one shows only SNI hostnames (`www.gstatic.com`, `aisandbox-pa.googleapis.com` in run 201).

## Session log: what was tried on 2026-09-27

Done and working:
- SDK command-line tools, `tls33` AVD, `root` / `disable-verity` / `remount`, PCAPdroid + mitm add-on installed, mitm CA copied to the system store (shows under Trusted credentials > System).
- `com.mobilerun.portal-0.7.25.apk` (the crawler's accessibility Portal) installs on the emulator (`adb -s emulator-5554 install ...`); no native code, no ABI problem.

Failed:
- Flow from the phone's APKs (`00_base.apk` + arm64/xxhdpi splits): `INSTALL_FAILED_NO_MATCHING_ABIS` (res=-113). Only x86 code runs on this image, so Flow needs an x86_64/universal build (none found yet) or ARM translation added to `/system` (untested).

Wikipedia test (a pure-Java app, APKMirror build `4arch_7dpi`, installed OK):
- A manual PCAPdroid capture showed connections to `en.wikipedia.org`, `upload.wikimedia.org` etc. as `HTTPS, 443`.
- Connection #7's Payload tab was still **encrypted**: records start `17 03 03` (TLS application data), no readable HTTP.
- Its Overview had **no decryption line** and `App: Unknown (-1)`. Reading: decryption was not attempted for this capture (a failed attempt should report an error there). Not confirmed.

Next steps when resuming:
1. In PCAPdroid: confirm TLS decryption is on and the mitm add-on is enabled; select **Wikipedia** as the target app (not "all"); start a **new** capture; reload articles; re-open a connection and read the Overview decryption line.
2. If it reports an error: check the CA is still under Trusted credentials > System after the reboot, then consider pinning (Frida).
3. Only then return to Flow (x86_64 build or ARM translation) and to a crawler run on `emulator-5554`.
