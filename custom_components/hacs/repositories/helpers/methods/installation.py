# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from custom_components.hacs.helpers.install import install_repository


class RepositoryMethodPreInstall:
    async def async_pre_install(self) -> None:
        pass

    async def _async_pre_install(self) -> None:
        self.logger.info("Running pre installation steps")
        await self.async_pre_install()
        self.logger.info("Pre installation steps competed")


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


class RepositoryMethodPostInstall:
    async def async_post_install(self) -> None:
        pass

    async def _async_post_install(self) -> None:
        self.logger.info("Running post installation steps")
        await self.async_post_install()
        self.data.new = False
        self.hacs.hass.bus.async_fire(
            "hacs/repository",
            {"id": 1337, "action": "install", "repository": self.data.full_name},
        )
        self.logger.info("Post installation steps competed")
