# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
import os


class RepositoryMethodExsistOnLocalFS:
    def exsist_on_local_fs(self) -> bool:
        return os.path.exists(self.content.path.local)

    async def async_exsist_on_local_fs(self) -> bool:
        return await self.hacs.hass.async_add_executor_job(self.exsist_on_local_fs)
