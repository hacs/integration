from custom_components.hacs.helpers.classes.check import (
    RepositoryActionCheck,
    RepositoryCheckException,
)


class HacsManifest(RepositoryActionCheck):
    def check(self):
        if "hacs.json" not in [x.filename for x in self.repository.tree]:
            raise RepositoryCheckException("The repository has no 'hacs.json' file")
