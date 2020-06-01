# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from custom_components.hacs.helpers.install import install_repository


class RepositoryMethodInstall:
    async def install(self) -> None:
        self.logger.warning("'install' is deprecated, use 'async_install' instead")
        await self.async_install()

    async def async_install(self) -> None:
        await self._async_pre_install()
        self.logger.info("Running installation steps")
        await install_repository(self)
        self.logger.info("Installation steps competed")
        await self._async_post_install()
