from custom_components.hacs.helpers.classes.validate import (
    ActionValidationBase,
    ValidationException,
)


class IntegrationManifest(ActionValidationBase):
    def check(self):
        if "manifest.json" not in [x.filename for x in self.repository.tree]:
            raise ValidationException("The repository has no 'hacs.json' file")
