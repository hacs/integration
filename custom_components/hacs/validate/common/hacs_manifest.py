from custom_components.hacs.helpers.classes.validate import (
    ActionValidationBase,
    ValidationException,
)


class HacsManifest(ActionValidationBase):
    def check(self):
        if "hacs.json" not in [x.filename for x in self.repository.tree]:
            raise ValidationException("The repository has no 'hacs.json' file")
