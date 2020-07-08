from custom_components.hacs.helpers.classes.check import (
    RepositoryCheck,
    RepositoryCheckException,
)


class RepositoryDescription(RepositoryCheck):
    def check(self):
        if self.repository.data.description is None:
            raise RepositoryCheckException("The repository has no description")
