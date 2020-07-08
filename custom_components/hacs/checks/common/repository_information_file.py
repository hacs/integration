from custom_components.hacs.helpers.classes.check import (
    RepositoryActionCheck,
    RepositoryCheckException,
)


class RepositoryInformationFile(RepositoryActionCheck):
    async def async_check(self):
        filenames = [x.filename.lower() for x in self.repository.tree]
        if self.repository.data.render_readme and "readme" in filenames:
            pass
        elif self.repository.data.render_readme and "readme.md" in filenames:
            pass
        elif "info" in filenames:
            pass
        elif "info.md" in filenames:
            pass
        else:
            raise RepositoryCheckException("The repository has no information file")
