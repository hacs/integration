"""HACS Configuration."""


class Configuration:
    """Configuration class."""

    def __init__(self, config):
        """Initialize."""
        self.config = config
        self.frontend_mode = "Grid"
        self.config_type = None
        self.config_entry = None

    @property
    def token(self):
        """GitHub Access token."""
        if self.config.get("token") is not None:
            return self.config["token"]
        return None

    @property
    def sidepanel_title(self):
        """Sidepanel title."""
        if self.config.get("sidepanel_title") is not None:
            return self.config["sidepanel_title"]
        return "Community"

    @property
    def sidepanel_icon(self):
        """Sidepanel icon."""
        if self.config.get("sidepanel_icon") is not None:
            return self.config["sidepanel_icon"]
        return "mdi:alpha-c-box"

    @property
    def dev(self):
        """Dev mode active."""
        if self.config.get("dev") is not None:
            return self.config["dev"]
        return False

    @property
    def plugin_path(self):
        """Plugin path."""
        if self.config.get("plugin_path") is not None:
            return self.config["plugin_path"]
        return "www/community/"

    @property
    def appdaemon(self):
        """Enable appdaemon."""
        if self.config.get("appdaemon") is not None:
            return self.config["appdaemon"]
        return False

    @property
    def appdaemon_path(self):
        """Appdaemon apps path."""
        if self.config.get("appdaemon_path") is not None:
            return self.config["appdaemon_path"]
        return "appdaemon/apps/"

    @property
    def python_script(self):
        """Enable python_script."""
        if self.config.get("python_script") is not None:
            return self.config["python_script"]
        return False

    @property
    def python_script_path(self):
        """python_script path."""
        if self.config.get("python_script_path") is not None:
            return self.config["python_script_path"]
        return "python_scripts/"

    @property
    def theme(self):
        """Enable theme."""
        if self.config.get("theme") is not None:
            return self.config["theme"]
        return False

    @property
    def theme_path(self):
        """Themes path."""
        if self.config.get("theme_path") is not None:
            return self.config["theme_path"]
        return "themes/"
