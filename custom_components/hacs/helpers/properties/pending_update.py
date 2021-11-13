# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from abc import ABC

from awesomeversion import AwesomeVersion, AwesomeVersionException


class RepositoryPropertyPendingUpdate(ABC):
    @property
    def pending_update(self) -> bool:
        if not self.can_install:
            return False
        if self.data.installed:
            if self.data.selected_tag is not None:
                if self.data.selected_tag == self.data.default_branch:
                    if self.data.installed_commit != self.data.last_commit:
                        return True
                    return False
            if self.display_version_or_commit == "version":
                try:
                    return AwesomeVersion(self.display_available_version) > AwesomeVersion(
                        self.display_installed_version
                    )
                except AwesomeVersionException:
                    pass
            if self.display_installed_version != self.display_available_version:
                return True

        return False

    @property
    def pending_upgrade(self) -> bool:
        """kept for legacy compatibility"""
        return self.pending_update
