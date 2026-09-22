---
generated: true
file: src/mobile_crawler/infrastructure/docker_autostart.py
---
# mobile_crawler.infrastructure.docker_autostart

Auto-start the MobSF/OmniParser Docker containers a crawl will need.

Source: `src/mobile_crawler/infrastructure/docker_autostart.py`

## Functions
- `ensure_mobsf_running_if_enabled`
- `ensure_omniparser_running_if_enabled`

## Imports
- [[code/config/config_manager|config.config_manager]]
- [[code/infrastructure/mobsf_docker|infrastructure.mobsf_docker]]
- [[code/infrastructure/omniparser_docker|infrastructure.omniparser_docker]]

## Imported by
- [[code/cli/commands/crawl|cli.commands.crawl]]
- [[code/cli/commands/mobsf_scan|cli.commands.mobsf_scan]]
