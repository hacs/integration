from custom_components.hacs.helpers.classes.check import (
    RepositoryCheck,
    RepositoryCheckException,
)


class HacsManifest(RepositoryCheck):
    def check(self):
        if not self.action:
            return
        if "hacs.json" not in [x.filename for x in self.repository.tree]:
            raise RepositoryCheckException("The repository has no 'hacs.json' file")
