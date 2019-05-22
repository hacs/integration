"""Element class"""


class Element:
    """Element Class"""

    def __init__(self, element_type, name):
        """Set up an element."""
        self.authors = []
        self.avaiable_version = None
        self.description = ""
        self.element_id = name
        self.element_type = element_type
        self.info = None
        self.installed_version = None
        self.isinstalled = False
        self.last_update = None
        self.manifest = None
        self.name = name
        self.releases = None
        self.remote_dir_location = None
        self.repo = None
        self.restart_pending = False
        self.trackable = False
