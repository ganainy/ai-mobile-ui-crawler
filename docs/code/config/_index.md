---
generated: partial
---
# mobile_crawler.config

<!-- summary:start -->
Application configuration: config manager, defaults, paths.
<!-- summary:end -->

## Modules
- [[code/config/api_keys|config.api_keys]] - Where an API key comes from: the setting, then the saved secret, then the environment.
- [[code/config/config_manager|config.config_manager]] - Configuration manager with precedence: run overrides → SQLite → environment variables → module defaults.
- [[code/config/defaults|config.defaults]] - Default configuration values.
- [[code/config/paths|config.paths]] - Configuration utilities.
