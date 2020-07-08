from custom_components.hacs.helpers.classes.check import (
    RepositoryCheck,
    RepositoryCheckException,
)


class RepositoryDescription(RepositoryCheck):
    def check(self):
        if not self.repository.data.description:
            raise RepositoryCheckException("The repository has no description")
