"""Hacs repositories handler."""
from . import Hacs


class HacsRepositories(Hacs):
    """Hacs repositories handler."""

    repositories = []
    repository_types = {}

    async def register(self, repository_type, repo, repository=None):
        """Register new repository."""

    def register_repository_type(self, repository_type, repository_type_class):
        """Register repository type class."""
        if repository_type not in self.repository_types:
            self.repository_types[repository_type] = repository_type_class

    def get_by_id(self, repository_id):
        """Get repository by ID."""
        try:
            for repository in self.repositories:
                repository = self.repositories[repository]
                if repository.repository_id == repository_id:
                    return repository
        except Exception:  # pylint: disable=broad-except
            pass
        return None

    def get_by_name(self, name):
        """Get repository by name."""
        try:
            for repository in self.repositories:
                repository = self.repositories[repository]
                if repository.repository_name == name:
                    return repository
        except Exception:  # pylint: disable=broad-except
            pass
        return None

    def is_known(self, repository_full_name):
        """Return a bool if the repository is known."""
        for repository in self.repositories:
            repository = self.repositories[repository]
            if repository.repository_name == repository_full_name:
                return True
        return False

    @property
    def sorted_by_name(self):
        """Return a sorted(by name) list of repository objects."""
        sortedlist = []
        for repository in self.repositories:
            sortedlist.append(self.repositories[repository])
        return sorted(sortedlist, key=lambda x: x.name.lower())

    @property
    def sorted_by_repository_name(self):
        """Return a sorted(by repository_name) list of repository objects."""
        sortedlist = []
        for repository in self.repositories:
            sortedlist.append(self.repositories[repository])
        return sorted(sortedlist, key=lambda x: x.repository_name)
