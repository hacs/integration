from custom_components.hacs.validate.base import (
    ValidationBase,
    ValidationException,
)


class RepositoryTopics(ValidationBase):
    def check(self):
        if not self.repository.data.topics:
            raise ValidationException("The repository has no description")
