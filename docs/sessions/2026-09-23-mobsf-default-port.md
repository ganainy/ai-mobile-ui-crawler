---
author: claude
date: 2026-09-23
---
# MobSF default URL on MobSF's port (#28)

**Ask:** issue #28. The default `mobsf_api_url` was `http://localhost:8001`, which is OmniParser's port. The MobSF container is published on 8000, so with defaults auto-start worked but API calls went to OmniParser.

**Done** (worktree branch `issue-28-mobsf-port`):
- `config/defaults.py` defines `MOBSF_DEFAULT_URL = "http://localhost:8000"` once; `DEFAULTS["mobsf_api_url"]`, `MobSFManager`'s fallbacks, `main_window.py` and the Settings panel (placeholder, load default, blank-save value, validation examples) all use it.
- `MobSFDockerService(url=MOBSF_DEFAULT_URL, image, container_name)` takes its host port from the URL, like `OmniParserDockerService`. `MOBSF_PORT` is gone; `MOBSF_CONTAINER_PORT = 8000` is the port inside the container (`-p <url port>:8000`). The CLI auto-start (`docker_autostart.py`) and the GUI (`start_mobsf_if_enabled`) pass the configured URL.
- Old saved value: `correct_mobsf_api_url` (`config/defaults.py`) turns a saved local MobSF URL on OmniParser's port (localhost/127.0.0.1:8001) into the new default. `ConfigManager.get` applies it to the SQLite value, so the CLI and `MobSFManager` get it too, and the Settings panel applies it on load. Without that, a CLI user with the old saved 8001 would now have MobSF published on 8001. The user's own `user_config.db` already had 8000.
- Code review (two axes): the spec review and the standards review both found that the first version fixed the saved 8001 only in the Settings panel. That is now handled in the config layer as described above. Left as they are: the `or MOBSF_DEFAULT_URL` repeated at the two call sites that build the service; `is_mobsf_reachable` still probes 127.0.0.1 whatever host the URL names; `OMNIPARSER_DEFAULT_URL` still lives in `omniparser_docker.py`.
- Tests: default ports differ (`tests/config/test_defaults.py`), port from URL + `-p` mapping (`test_mobsf_docker.py`), auto-start passes the configured URL (`test_docker_autostart.py`), Settings default/correction (`test_settings_panel.py`). `tests/cli/test_crawl_command.py` gained an autouse fixture that stubs Docker auto-start: those tests use a `Mock` config and were running the real MobSF auto-start.
- Full suite green. No typechecker installed in `.venv312`. Not tried against a real MobSF container.
