from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.hacs.enums import HacsCategory

from .base import ActionValidationBase, ValidationException

if TYPE_CHECKING:
    from ..repositories.base import HacsRepository

URL = "https://rc.home-assistant.io/integrations.json"


async def async_setup_validator(repository: HacsRepository) -> Validator:
    """Set up this validator."""
    return Validator(repository=repository)


class Validator(ActionValidationBase):
    """Validate the repository."""

    more_info = "https://hacs.xyz/docs/publish/include#check-domain-override"
    categories = (HacsCategory.INTEGRATION,)

    async def async_validate(self) -> None:
        """Validate the repository."""
        response = await self.hacs.session.get(URL)
        content = await response.json()

        domain = self.repository.data.domain
        if domain in content:
            raise ValidationException(
                f"The integration uses domain '{domain}' which is a core Home Assistant "
                "integration. Custom integrations must not override core integrations."
            )
