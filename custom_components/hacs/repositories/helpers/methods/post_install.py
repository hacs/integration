# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member


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
