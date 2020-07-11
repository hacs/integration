from custom_components.hacs.helpers.classes.validate import (
    ValidationBase,
    ValidationException,
)


class RepositoryDescription(ValidationBase):
    def check(self):
        if not self.repository.data.description:
            raise ValidationException("The repository has no description")
