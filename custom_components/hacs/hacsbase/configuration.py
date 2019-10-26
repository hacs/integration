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
        return Configuration(
            config=configuration,
            options=options,
            appdaemon=configuration["appdaemon"],
            python_script=configuration["python_script"],
            sidepanel_icon=configuration["sidepanel_icon"],
            sidepanel_title=configuration["sidepanel_title"],
            theme=configuration["theme"],
            token=configuration["token"],
            country=options["country"],
            experimental=options["experimental"],
            release_limit=options["release_limit"],
        )
