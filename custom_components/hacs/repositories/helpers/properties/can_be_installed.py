# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from custom_components.hacs.helpers.misc import version_left_higher_then_right


class RepositoryPropertyCanBeInstalled:
    @property
    def can_be_installed(self) -> bool:
        if self.data.homeassistant is not None:
            if self.data.releases:
                if not version_left_higher_then_right(
                    self.hacs.system.ha_version, self.data.homeassistant
                ):
                    return False
        return True

    @property
    def can_install(self):
        """kept for legacy compatibility"""
        return self.can_be_installed
