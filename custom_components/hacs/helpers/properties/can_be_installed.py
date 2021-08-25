# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from abc import ABC

from custom_components.hacs.helpers.functions.misc import version_left_higher_then_right


class RepositoryPropertyCanBeInstalled(ABC):
    @property
    def can_be_installed(self) -> bool:
        if self.data.homeassistant is not None:
            if self.data.releases:
                if not version_left_higher_then_right(
                    self.hacs.core.ha_version, self.data.homeassistant
                ):
                    return False
        return True

    @property
    def can_install(self):
        """kept for legacy compatibility"""
        return self.can_be_installed
