"""Auto-start the MobSF/OmniParser Docker containers a crawl will need.

Ports ``MainWindow.start_mobsf_if_enabled`` / ``start_omniparser_if_enabled``
to a blocking call, for callers with no UI thread to keep responsive (the
CLI's ``crawl`` command and, later, ``mobsf-scan``). Containers are left
running afterwards, matching GUI behavior.
"""

from mobile_crawler.config.config_manager import ConfigManager
from mobile_crawler.config.defaults import OMNIPARSER_DEFAULT_URL
from mobile_crawler.infrastructure.mobsf_docker import MobSFDockerService
from mobile_crawler.infrastructure.omniparser_docker import OmniParserDockerService


def ensure_mobsf_running_if_enabled(config_manager: ConfigManager) -> tuple[bool, str] | None:
    """Start MobSF if ``enable_mobsf_analysis`` is on and it isn't already running.

    Returns None if MobSF analysis isn't enabled (nothing to do), otherwise
    the (success, message) result of starting it.
    """
    if not config_manager.get("enable_mobsf_analysis", False):
        return None
    return MobSFDockerService(config_manager.get("mobsf_api_url")).prepare()


def ensure_omniparser_running_if_enabled(config_manager: ConfigManager) -> tuple[bool, str] | None:
    """Start the local OmniParser stack if configured to use it and not already running.

    Returns None if the local OmniParser backend isn't in use (nothing to
    do), otherwise the (success, message) result of starting it.
    """
    if config_manager.get("ui_parser_mode", "boost") == "accessibility":
        return None
    if config_manager.get("omniparser_backend", "replicate") != "local":
        return None

    url = config_manager.get("omniparser_local_url", OMNIPARSER_DEFAULT_URL)
    return OmniParserDockerService(url).ensure_running()
