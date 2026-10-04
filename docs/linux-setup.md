# Linux Setup Guide

This is the Linux counterpart of the Windows/PowerShell instructions in the [README](../README.md). It was written while setting the project up on a Debian 13 host (x86_64) with a Samsung phone on Android 15 connected over wireless ADB. Each step says whether it was **verified** on that host or only taken from the README.

Commands are for `bash`. No `sudo` is needed except where noted.

## 1. Python 3.12

`pyproject.toml` requires Python `>=3.12,<3.13`. Many distributions ship 3.13 or newer, so use [uv](https://docs.astral.sh/uv/) to get a 3.12 interpreter without touching the system Python:

```bash
git clone https://github.com/ganainy/ai-mobile-ui-crawler
cd ai-mobile-ui-crawler

uv venv --python 3.12 .venv312
source .venv312/bin/activate
uv pip install -e .
mobile-crawler-cli --help
```

Verified. Plain `python3.12 -m venv .venv312 && pip install -e .` also works if 3.12 is installed.

### Tracing packages (needed for Phoenix)

`pip install -e .` does not install the OpenTelemetry/OpenInference packages that tracing needs. Without them a crawl logs `Failed to set up Phoenix tracing: No module named 'openinference'` and runs untraced. Install them once:

```bash
uv pip install openinference-instrumentation-llama-index opentelemetry-exporter-otlp-proto-http
```

Verified: with these two packages installed, traces from a crawl show up in Phoenix.

## 2. ADB (Android Platform Tools)

If `adb` is not packaged for your distribution, or you have no root, use Google's archive:

```bash
mkdir -p ~/android && cd ~/android
curl -LO https://dl.google.com/android/repository/platform-tools-latest-linux.zip
unzip platform-tools-latest-linux.zip && rm platform-tools-latest-linux.zip
echo 'export PATH=$HOME/android/platform-tools:$PATH' >> ~/.bashrc
export PATH=$HOME/android/platform-tools:$PATH
adb version
```

Verified. On Debian/Ubuntu `sudo apt install adb` is the alternative.

### USB

Enable Developer options and USB debugging on the phone (see the README), plug it in, accept the prompt, then run `adb devices`. If the device shows as `no permissions`, add a udev rule for your phone's vendor or run `adb kill-server` and retry.

### Wireless debugging (Android 11+)

The phone and the Linux host must be on the same network. Pairing and connecting use **different ports**, and both change when Wireless debugging is toggled or the phone restarts.

1. On the phone: Developer options > **Wireless debugging** > on.
2. Tap **Pair device with pairing code**. Keep that popup open. It shows `IP:pairing-port` and a 6-digit code.
3. On the host:

   ```bash
   adb pair <IP>:<pairing-port>      # type the 6-digit code when asked
   ```

4. Close the popup. The main Wireless debugging screen shows the **connection** port (a different number). If you don't have it, ask mDNS:

   ```bash
   adb mdns services                 # prints <IP>:<connection-port>
   adb connect <IP>:<connection-port>
   adb devices                       # the phone should be listed as "device"
   ```

Verified. Pairing normally survives reboots (not tested here); after a port change run `adb mdns services` and `adb connect` again. Keep the screen on and the phone charging during long crawls, because Android drops the wireless link when the network changes.

Use the connected ID as `--device`, for example `--device 192.168.1.50:41234`.

### Accessibility Portal

```bash
mobile-crawler-cli a11y-portal status --device <IP>:<port>
```

Prints `Portal <version> is ready` once Portal is installed with its accessibility service on (`a11y-portal enable` / `install` fix it over adb).

## 3. AI provider key

API keys come from persisted settings or environment variables. For example for OpenCode Go:

```bash
export OPENCODE_GO_API_KEY=...        # keep it out of shell history and chat
```

Put the line in a file with mode `600` (for example `~/.config/mobile-crawler.env`) and load it with `set -a; . that-file; set +a`. Do not leave two different values for the same variable in that file; the last one wins, and an invalid last line makes every call fail with `401 Invalid credential`.

Smoke test of one step, which also confirms ADB, the Portal and the provider:

```bash
mobile-crawler-cli crawl --device <IP>:<port> --package <app.package.id> \
  --provider opencode_go --model deepseek-v4.1-flash --steps 1 --no-human-fallback
```

Verified with the `opencode_go` provider and `deepseek-v4.1-flash`. The list of model ids is public: `curl https://opencode.ai/zen/go/v1/models`.

## 4. Docker (Phoenix tracing and MobSF)

Both integrations only call the `docker` CLI, so nothing differs from Windows except installation. Install Docker Engine from your distribution or from <https://docs.docker.com/engine/install/>, then let your user talk to the daemon:

```bash
sudo usermod -aG docker "$USER"
# log out and back in, or for one command:
sg docker -c "docker ps"
```

`docker info` must succeed for the crawler to start containers. A shell that was started before the group change needs `sg docker -c "..."` (or a fresh login) or the crawler logs "permission denied" for `/var/run/docker.sock`.

### Phoenix (`mobile-crawler-phoenix`)

```bash
mobile-crawler-cli config set enable_tracing true
mobile-crawler-cli crawl ...          # starts the container itself
```

The CLI/GUI pull and start the `mobile-crawler-phoenix` container (image `arizephoenix/phoenix:version-20.3.0`) on `127.0.0.1:6006` and keep traces in `~/.phoenix`. To start it by hand:

```bash
docker run -d --rm --name mobile-crawler-phoenix \
  -p 127.0.0.1:6006:6006 \
  -v "$HOME/.phoenix:/mnt/data" -e PHOENIX_WORKING_DIR=/mnt/data \
  arizephoenix/phoenix:version-20.3.0
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:6006/healthz    # 200
```

Verified: the managed container starts on Linux, `/healthz` returns 200 and spans from a crawl appear under the `default` project (`curl http://localhost:6006/v1/projects/default/spans`). Open `http://localhost:6006` for the UI. The image is about 1.5 GB on disk.

### MobSF (`mobile-crawler-mobsf`)

```bash
docker pull opensecurity/mobile-security-framework-mobsf
docker run --rm -it --name mobile-crawler-mobsf -p 8000:8000 opensecurity/mobile-security-framework-mobsf
```

Then run a crawl with `--enable-mobsf-analysis`. The API key is read from `.mobsf_api_key` in the repo root, or from the container logs. Write it with `echo '<key>' > .mobsf_api_key`.

**Not verified.** These are the README commands translated to bash. The test host did not have the several GB of free disk and the RAM (MobSF wants roughly 2 GB or more) to run it.

## 5. Disk and memory

Docker images add up: Phoenix is about 1.5 GB and MobSF is several GB once unpacked. Check `df -h /var/lib/docker` before pulling. `uv cache clean` frees a lot of space if you used uv.

## 6. Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `failed to connect ... Connection refused` after it worked | The wireless-debugging port changed. Run `adb mdns services`, then `adb connect` with the new port. |
| `adb pair` says `protocol fault` | The pairing popup was closed, or the code and port do not belong together. Reopen the popup and use its current IP:port and code. |
| `401 Invalid credential` from OpenCode Go | The key is invalid or a duplicate invalid line shadows the good one. Check the env file. |
| `Unable to open target app ... current_package=None` | The app shows a popup window that takes focus, so the crawler cannot read the package from `mCurrentFocus`. Try again from the home screen; some apps (for example Google Translate) trigger this consistently. |
| `Unable to open target app ... current_package=<other package>` | The launcher activity belongs to a different package than the one given (for example `com.android.settings` opens `com.android.settings.intelligence`). Pick another app or package id. |
| `permission denied ... docker.sock` | Your shell does not have the `docker` group yet. Use `sg docker -c "..."` or log in again. |
| `No module named 'openinference'` | Install the tracing packages from section 1. |
| `OmniParser backend 'replicate' not available` | The accessibility tree was incomplete and no OmniParser backend is configured. The crawl continues without it. |
