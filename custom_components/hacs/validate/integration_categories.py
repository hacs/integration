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

        manifest = await self.repository.async_get_loaded_integration_manifest()
        if "categories" not in manifest:
            self.repository.logger.warning(
                "%s The integration manifest has no categories, see %s",
                self.repository.string,
                self.more_info,
            )
            return

        try:
            INTEGRATION_MANIFEST_CATEGORIES_SCHEMA(manifest)
        except Invalid as exception:
            raise ValidationException(humanize_error(manifest, exception)) from exception
