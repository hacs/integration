# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from abc import ABC

from custom_components.hacs.utils.version import version_left_higher_then_right


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
                if version_left_higher_then_right(
                    self.display_available_version,
                    self.display_installed_version,
                ):
                    return True
            if self.display_installed_version != self.display_available_version:
                return True

        return False

    @property
    def pending_upgrade(self) -> bool:
        """kept for legacy compatibility"""
        return self.pending_update
