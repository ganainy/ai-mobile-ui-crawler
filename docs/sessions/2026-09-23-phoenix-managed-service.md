---
author: claude
date: 2026-09-23
---
# Phoenix as a Managed Service (#27)

Implemented [#27](https://github.com/ganainy/ai-mobile-ui-crawler/issues/27) in worktree branch `issue-27-phoenix-docker`.

## Built
- `infrastructure/phoenix_docker.py` `PhoenixDockerService`: `docker run -d --rm --name mobile-crawler-phoenix -p 127.0.0.1:<port>:6006 -v ~/.phoenix:/mnt/data -e PHOENIX_WORKING_DIR=/mnt/data arizephoenix/phoenix:version-20.3.0`; health check `GET /healthz`. Order: Phoenix answers -> reuse; port open but not Phoenix -> no start; no Docker / run error / no `/healthz` in 90 s -> failure. The last failure per port is kept (`last_start_error`) so the Pre-run Warning can quote it. `is_local_phoenix_url`: only `localhost` / `127.0.0.1` are managed.
- `docker_autostart.ensure_phoenix_running_if_enabled` (tracing on, provider `phoenix`, local URL). CLI `crawl` calls it next to MobSF/OmniParser; prints success on stderr, leaves a failure to the Pre-run Warning (so it isn't printed twice); container left running.
- `pre_run_warnings._phoenix_warning`: remote URL down -> "not on this machine, the crawler does not start it"; port held by something else; otherwise "could not be started in Docker (<reason>)".
- GUI: `start_phoenix_if_enabled` at launch, when the tracing checkbox is ticked (new `SettingsPanel.tracing_enabled` signal) and on settings save; before each crawl `_wait_for_phoenix_before_crawl` (busy dialog after 0.5 s with a Skip button, crawl goes on either way); Phoenix is the third checkbox in the exit dialog. Startup failures are only logged (the pre-crawl warning dialog shows them).
- `pyproject.toml` `arize` extra: `arize-phoenix` replaced by `opentelemetry-exporter-otlp-proto-http` (what `telemetry/phoenix.py` actually imports). `llama-index-callbacks-arize-phoenix` kept: it imports `phoenix` only in its v1 fallback, and our code doesn't use it anyway.
- Docs: `docs/cli.md` "Tracing (Phoenix)" under Optional features, README paragraph.

## Code review fixes
- Our own container holding the port while still booting (or hung) was reported as "port in use by something that is not Phoenix" and never waited for: `ensure_running` now checks `is_running()` before calling it a conflict and waits; the warning says "does not answer yet, see `docker logs`".
- A stopped container, or one running on another port after the Phoenix URL changed, is replaced (`docker rm -f` + run).
- The warning's fix line matches the cause ("fix the error above" / "check that Docker Desktop is running") instead of always "start Docker Desktop".
- Settings' Phoenix hint no longer says to run `phoenix serve`.
- The "tracing on + phoenix + URL (+ local)" check is in one place (`phoenix_tracing_url` / `managed_phoenix_url`); signal renamed `tracing_turned_on`.
- `CONTEXT.md` **Managed Service** / Pre-run Warning wording lives in `main`'s uncommitted grill-session edit, not in this branch.

## Verified
- Real Docker run on port 16006 with a temp bind-mount dir: image pulled + started in 137 s, 20 OTLP spans written and read back over REST, `phoenix.db` + WAL files on the Windows bind mount, reuse and stop worked. Tag `version-20.3.0` exists.
- Suite green (1804 passed after the review fixes and the uninstall).

## Not done / open
- `arize-phoenix` uninstalled from `.venv312` with the user's OK (after they stopped their `phoenix serve`); `phoenix.client`/`evals`/`otel` (other packages) remain, `phoenix.server` is gone. Suite still green.
- Not tried against the real `~/.phoenix/phoenix.db` or in a real crawl / the real GUI.
