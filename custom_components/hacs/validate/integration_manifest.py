from __future__ import annotations

from voluptuous.error import Invalid

from ..enums import HacsCategory, RepositoryFile
from ..repositories.base import HacsRepository
from ..repositories.integration import HacsIntegrationRepository
from ..utils.validate import INTEGRATION_MANIFEST_JSON_SCHEMA
from .base import ActionValidationBase, ValidationException


async def async_setup_validator(repository: HacsRepository) -> Validator:
    """Set up this validator."""
    return Validator(repository=repository)


class Validator(ActionValidationBase):
    """Validate the repository."""

    repository: HacsIntegrationRepository
    more_info = "https://hacs.xyz/docs/publish/include#check-manifest"
    categories = [HacsCategory.INTEGRATION]

    async def async_validate(self):
        """Validate the repository."""
        if RepositoryFile.MAINIFEST_JSON not in [x.filename for x in self.repository.tree]:
            raise ValidationException(
                f"The repository has no '{RepositoryFile.MAINIFEST_JSON}' file"
            )

        content = await self.repository.async_get_integration_manifest(self.repository.ref)
        try:
            INTEGRATION_MANIFEST_JSON_SCHEMA(content)
        except Invalid as exception:
            raise ValidationException(exception) from exception
