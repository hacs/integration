from __future__ import annotations

from typing import TYPE_CHECKING

from voluptuous.error import Invalid
from voluptuous.humanize import humanize_error

from ..enums import HacsCategory, RepositoryFile
from ..utils.validate import INTEGRATION_MANIFEST_CATEGORIES_SCHEMA
from .base import ActionValidationBase, ValidationException

if TYPE_CHECKING:
    from ..repositories.base import HacsRepository
    from ..repositories.integration import HacsIntegrationRepository


async def async_setup_validator(repository: HacsRepository) -> Validator:
    """Set up this validator."""
    return Validator(repository=repository)


class Validator(ActionValidationBase):
    """Validate the repository."""

    repository: HacsIntegrationRepository
    more_info = "https://contributors.home-assistant.io/core/integrations/categories/"
    categories = (HacsCategory.INTEGRATION,)

    async def async_validate(self) -> None:
        """Validate the repository."""
        # The integration_manifest check reports a missing manifest
        if RepositoryFile.MAINIFEST_JSON not in [x.filename for x in self.repository.tree]:
            return

        content = await self.repository.get_integration_manifest(version=self.repository.ref)
        try:
            INTEGRATION_MANIFEST_CATEGORIES_SCHEMA(content)
        except Invalid as exception:
            raise ValidationException(humanize_error(content, exception)) from exception
