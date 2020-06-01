# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member


class RepositoryMethodPreInstall:
    async def async_pre_install(self) -> None:
        pass

    async def _async_pre_install(self) -> None:
        self.logger.info("Running pre installation steps")
        await self.async_pre_install()
        self.logger.info("Pre installation steps competed")
