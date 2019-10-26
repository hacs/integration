"""HACS Configuration."""
# pylint: disable=too-many-instance-attributes, too-few-public-methods
import attr


@attr.s(auto_attribs=True)
class Configuration:
    """Configuration class."""

    # Main configuration:
    appdaemon_path: str = "appdaemon/apps/"
    appdaemon: bool = False
    config: dict = {}
    config_entry: dict = None
    config_type: str = None
    dev: bool = False
    frontend_mode: str = "Grid"
    options: dict = {}
    plugin_path: str = "www/community/"
    python_script_path: str = "python_scripts/"
    python_script: bool = False
    sidepanel_icon: str = None
    sidepanel_title: str = None
    theme_path: str = "themes/"
    theme: bool = False
    token: str = None

    # Config options:
    country: str = "ALL"
    experimental: bool = False
    release_limit: int = 5

    def from_dict(self, configuration: dict, options: dict) -> None:
        """Set attributes from dict."""
        self.config = configuration
        self.options = options

        self.appdaemon = configuration["appdaemon"]
        self.python_script = configuration["python_script"]
        self.sidepanel_icon = configuration["sidepanel_icon"]
        self.sidepanel_title = configuration["sidepanel_title"]
        self.theme = configuration["theme"]
        self.token = configuration["token"]

        self.country = options["country"]
        self.experimental = options["experimental"]
        self.release_limit = options["release_limit"]
