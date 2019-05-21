"""Element class"""


class Element:
    """Element Class"""

    def __init__(self, element_type, name):
        """Set up an element."""
        self.element_id = name
        self.name = name
        self.element_type = element_type
        self.description = ""
        self.repo = None
        self.restart_pending = False
        self.isinstalled = False
        self.installed_version = None
        self.avaiable_version = None
        self.info = None
        self.manifest = None
        self.remote_dir_location = None
        self.authors = []
