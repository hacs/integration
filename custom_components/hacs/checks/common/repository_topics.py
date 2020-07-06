from custom_components.hacs.helpers.classes.check import (
    RepositoryCheck,
    RepositoryCheckException,
)


class RepositoryTopics(RepositoryCheck):
    def check(self):
        if not self.repository.data.topics:
            raise RepositoryCheckException("The repository has no description")
