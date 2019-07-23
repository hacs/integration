"""Hacs repositories handler."""
from . import Hacs


class HacsRegistry:
    """HacsRegistry"""

    repositories = []


class HacsRepositories(Hacs):
    """Hacs repositories handler."""

    registry = HacsRegistry()

    def get_by_id(self, repository_id):
        """Get repository by ID."""
        try:
            for repository in self.registry.repositories:
                if repository.repository_id == repository_id:
                    return repository
        except Exception:  # pylint: disable=broad-except
            pass
        return None

    def get_by_name(self, name):
        """Get repository by name."""
        try:
            for repository in self.registry.repositories:
                if repository.repository_name == name:
                    return repository
        except Exception:  # pylint: disable=broad-except
            pass
        return None

    def is_known(self, repository_full_name):
        """Return a bool if the repository is known."""
        for repository in self.registry.repositories:
            if repository.repository_name == repository_full_name:
                return True
        return False

    @property
    def sorted_by_name(self):
        """Return a sorted(by name) list of repository objects."""
        sortedlist = []
        for repository in self.registry.repositories:
            sortedlist.append(self.registry.repositories[repository])
        return sorted(sortedlist, key=lambda x: x.name.lower())

    @property
    def sorted_by_repository_name(self):
        """Return a sorted(by repository_name) list of repository objects."""
        sortedlist = []
        for repository in self.registry.repositories:
            sortedlist.append(self.registry.repositories[repository])
        return sorted(sortedlist, key=lambda x: x.repository_name)
