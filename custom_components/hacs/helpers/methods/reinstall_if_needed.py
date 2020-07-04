# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from abc import ABC

from custom_components.hacs.helpers.functions.path_exsist import async_path_exsist


class RepositoryMethodReinstallIfNeeded(ABC):
    async def async_reinstall_if_needed(self) -> None:
        if self.data.installed:
            if not await async_path_exsist(self.content.path.local):
                self.logger.error("Missing from local FS, should be reinstalled.")
                # await self.async_install()
