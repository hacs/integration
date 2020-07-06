from custom_components.hacs.helpers.classes.check import (
    RepositoryCheck,
    RepositoryCheckException,
)


class RepositoryReadme(RepositoryCheck):
    async def async_check(self):
        if not self.action:
            return
        filenames = [x.filename.lower() for x in self.repository.tree]
        if "info.md" not in filenames:
            raise RepositoryCheckException("The repository has no information file")
