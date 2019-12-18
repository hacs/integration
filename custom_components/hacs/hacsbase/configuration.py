"""HACS Configuration."""
import attr

from custom_components.hacs.hacsbase.exceptions import HacsUserScrewupException


@attr.s(auto_attribs=True)
class Configuration:
    """Configuration class."""

    # Main configuration:
    appdaemon_path: str = "appdaemon/apps/"
    appdaemon: bool = False
    config: dict = {}
    config_entry: dict = {}
    config_type: str = None
    debug: bool = False
    dev: bool = False
    frontend_mode: str = "Grid"
    frontend_compact: bool = False
    options: dict = {}
    onboarding_done: bool = False
    plugin_path: str = "www/community/"
    python_script_path: str = "python_scripts/"
    python_script: bool = False
    sidepanel_icon: str = "mdi:alpha-c-box"
    sidepanel_title: str = "Community"
    theme_path: str = "themes/"
    theme: bool = False
    token: str = None

    # Config options:
    country: str = "ALL"
    experimental: bool = False
    release_limit: int = 5

    @staticmethod
    def from_dict(configuration: dict, options: dict):
        """Set attributes from dicts."""
        if isinstance(options, bool) or isinstance(configuration.get("options"), bool):
            raise HacsUserScrewupException("Configuration is not valid.")

        if options is None:
            options = {}

        if not configuration:
            raise HacsUserScrewupException("Configuration is not valid.")

        config = Configuration()

        config.config = configuration
        config.options = options

        for conf_type in [configuration, options]:
            for key in conf_type:
                setattr(config, key, conf_type[key])

        return config
