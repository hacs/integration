from custom_components.hacs.enums import RepositoryFile
from custom_components.hacs.validate.base import (
    ActionValidationBase,
    ValidationException,
)


class HacsManifest(ActionValidationBase):
    def check(self):
        if RepositoryFile.HACS_JSON not in [x.filename for x in self.repository.tree]:
            raise ValidationException(f"The repository has no '{RepositoryFile.HACS_JSON}' file")
