# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
class RepositoryMethodReinstallIfNeeded:
    async def async_reinstall_if_needed(self) -> None:
        if self.data.installed:
            if not await self.async_exsist_on_local_fs():
                self.logger.error("Missing from local FS, should be reinstalled.")
                # await self.install()
