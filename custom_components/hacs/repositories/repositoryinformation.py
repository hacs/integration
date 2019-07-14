"""RepositoryInformation, used for the frontend."""
# pylint: disable=missing-docstring

class RepositoryInformation:

    def __init__(self, repository):
        self.repository = repository

    @property
    def name(self):
        if self.repository.repository_type != "integration":
            if self.repository.name:
                return self.repository.name.replace("-", " ").replace("_", " ").title()
            else:
                return self.repository_name.split("/")[-1]
        return self.repository.name

    @property
    def description(self):
        if self.repository.description is None:
            return ""
        return self.repository.description

    @property
    def custom(self):
        return self.repository.custom

    @property
    def new(self):
        return self.repository.new

    @property
    def track(self):
        return self.repository.track

    @property
    def hide(self):
        return self.repository.hide

    @property
    def installed(self):
        return self.repository.installed

    @property
    def repository_type(self):
        return self.repository.repository_type

    @property
    def repository_id(self):
        return self.repository.repository_id

    @property
    def repository_name(self):
        return self.repository.repository_name

    @property
    def selected_tag(self):
        return self.repository.selected_tag

    @property
    def published_tags(self):
        return self.repository.published_tags

    @property
    def default_branch(self):
        return self.repository.repository.default_branch

    @property
    def homeassistant_version(self):
        return self.repository.homeassistant_version

    @property
    def status(self):
        if self.repository.pending_restart:
            status = "pending-restart"
        elif self.repository.pending_update:
            status = "pending-update"
        elif self.repository.installed:
            status = "installed"
        else:
            status = "default"
        return status

    @property
    def status_description(self):
        description = {
            "default": "Not installed.",
            "pending-restart": "Restart pending.",
            "pending-update": "Update pending.",
            "installed": "No action required."
        }
        return description[self.status]

    @property
    def installed_version(self):
        if self.repository.version_installed is not None:
            installed = self.repository.version_installed
        else:
            if self.repository.installed_commit is not None:
                installed = self.repository.installed_commit
            else:
                installed = ""
        return installed

    @property
    def available_version(self):
        if self.repository.last_release_tag is not None:
            available = self.repository.last_release_tag
        else:
            if self.repository.last_commit is not None:
                available = self.repository.last_commit
            else:
                available = ""
        return available

    @property
    def topics(self):
        return str(self.repository.topics)

    @property
    def authors(self):
        if self.repository.authors:
            return str(self.repository.authors)
        return ""
