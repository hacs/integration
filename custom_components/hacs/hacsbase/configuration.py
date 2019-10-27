"""HACS Configuration."""
import attr


@attr.s(auto_attribs=True)
class Configuration:
    """Configuration class."""

    # Main configuration:
    appdaemon_path: str = "appdaemon/apps/"
    appdaemon: bool = False
    config: dict = {}
    config_entry: dict = {}
    config_type: str = ""
    dev: bool = False
    frontend_mode: str = "Grid"
    options: dict = {}
    plugin_path: str = "www/community/"
    python_script_path: str = "python_scripts/"
    python_script: bool = False
    sidepanel_icon: str = ""
    sidepanel_title: str = ""
    theme_path: str = "themes/"
    theme: bool = False
    token: str = ""

    # Config options:
    country: str = "ALL"
    experimental: bool = False
    release_limit: int = 5

    @staticmethod
    def from_dict(configuration: dict, options: dict):
        """Set attributes from dicts."""
        if options is None:
            options = {}
        return Configuration(
            config=configuration,
            options=options,
            appdaemon=configuration.get("appdaemon", False),
            python_script=configuration.get("python_script", False),
            sidepanel_icon=configuration.get("sidepanel_icon", "mdi:alpha-c-box"),
            sidepanel_title=configuration.get("sidepanel_title", "community"),
            theme=configuration.get("theme", False),
            token=configuration.get("token"),
            country=options.get("country", "ALL"),
            experimental=options.get("experimental", False),
            release_limit=options.get("release_limit", 5),
        )
