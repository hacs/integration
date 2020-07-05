"""HACS Configuration."""
import attr

from custom_components.hacs.helpers.classes.exceptions import HacsException
from custom_components.hacs.helpers.functions.logger import getLogger


@attr.s(auto_attribs=True)
class Configuration:
    """Configuration class."""

    # Main configuration:
    appdaemon_path: str = "appdaemon/apps/"
    appdaemon: bool = False
    netdaemon_path: str = "netdaemon/apps/"
    netdaemon: bool = False
    config: dict = {}
    config_entry: dict = {}
    config_type: str = None
    debug: bool = False
    dev: bool = False
    frontend_mode: str = "Grid"
    frontend_compact: bool = False
    frontend_repo: str = ""
    frontend_repo_url: str = ""
    options: dict = {}
    onboarding_done: bool = False
    plugin_path: str = "www/community/"
    python_script_path: str = "python_scripts/"
    python_script: bool = False
    sidepanel_icon: str = "hacs:hacs"
    sidepanel_title: str = "HACS"
    theme_path: str = "themes/"
    theme: bool = False
    token: str = None

    # Config options:
    country: str = "ALL"
    experimental: bool = False
    release_limit: int = 5

    def to_json(self):
        """Return a dict representation of the configuration."""
        return self.__dict__

    def print(self):
        """Print the current configuration to the log."""
        logger = getLogger("configuration")
        config = self.to_json()
        for key in config:
            if key in ["config", "config_entry", "options", "token"]:
                continue
            logger.debug(f"{key}: {config[key]}")

    @staticmethod
    def from_dict(configuration: dict, options: dict = None):
        """Set attributes from dicts."""
        if isinstance(options, bool) or isinstance(configuration.get("options"), bool):
            raise HacsException("Configuration is not valid.")

        if options is None:
            options = {}

        if not configuration:
            raise HacsException("Configuration is not valid.")

        config = Configuration()

        config.config = configuration
        config.options = options

        for conf_type in [configuration, options]:
            for key in conf_type:
                setattr(config, key, conf_type[key])

        return config
