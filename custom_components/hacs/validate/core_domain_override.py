from __future__ import annotations

from typing import TYPE_CHECKING

from ..enums import HacsCategory
from ..utils.json import json_loads
from .base import ActionValidationBase, ValidationException

if TYPE_CHECKING:
    from ..repositories.base import HacsRepository
    from ..repositories.integration import HacsIntegrationRepository

# The `next` site is generated from the upcoming Home Assistant release, so domains
# landing in the next release are caught before they ship, unlike `www`.
CORE_INTEGRATIONS_URL = "https://next.home-assistant.io/integrations.json"


async def async_setup_validator(repository: HacsRepository) -> Validator:
    """Set up this validator."""
    return Validator(repository=repository)


class Validator(ActionValidationBase):
    """Validate the repository."""

    repository: HacsIntegrationRepository
    more_info = "https://hacs.xyz/docs/publish/include#check-core-domain-override"
    categories = (HacsCategory.INTEGRATION,)

    async def async_validate(self) -> None:
        """Validate the repository."""
        if not (domain := self.repository.data.domain):
            # A missing or invalid manifest is reported by the integration_manifest check.
            return

        result = await self.hacs.async_download_file(CORE_INTEGRATIONS_URL, handle_rate_limit=True)
        if result is None:
            raise ValidationException("Could not fetch the core integrations list")

        try:
            core_domains = json_loads(result)
        except Exception as err:
            raise ValidationException("Could not parse the core integrations list") from err

        if not isinstance(core_domains, dict):
            raise ValidationException("Core integrations list has an unexpected format")

        if domain in core_domains:
            raise ValidationException(
                f"The integration overrides the core integration domain '{domain}'"
            )
