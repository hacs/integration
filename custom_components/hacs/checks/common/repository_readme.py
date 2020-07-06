from custom_components.hacs.helpers.classes.check import (
    RepositoryActionCheck,
    RepositoryCheckException,
)


class RepositoryReadme(RepositoryActionCheck):
    async def async_check(self):
        filenames = [x.filename.lower() for x in self.repository.tree]
        if "info.md" not in filenames:
            raise RepositoryCheckException("The repository has no information file")
