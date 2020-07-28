from custom_components.hacs.validate.base import (
    ActionValidationBase,
    ValidationException,
)


class RepositoryTopics(ActionValidationBase):
    def check(self):
        if not self.repository.data.topics:
            raise ValidationException("The repository has no description")
