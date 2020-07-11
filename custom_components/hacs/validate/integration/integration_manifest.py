from custom_components.hacs.validate.base import (
    ActionValidationBase,
    ValidationException,
)


class IntegrationManifest(ActionValidationBase, category="integration"):
    def check(self):
        if "manifest.json" not in [x.filename for x in self.repository.tree]:
            raise ValidationException("The repository has no 'hacs.json' file")
