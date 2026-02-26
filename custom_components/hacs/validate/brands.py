from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.hacs.enums import HacsCategory

from .base import ActionValidationBase, ValidationException

if TYPE_CHECKING:
    from ..repositories.base import HacsRepository

URL = "https://brands.home-assistant.io/domains.json"


async def async_setup_validator(repository: HacsRepository) -> Validator:
    """Set up this validator."""
    return Validator(repository=repository)


class Validator(ActionValidationBase):
    """Validate the repository."""

    more_info = "https://hacs.xyz/docs/publish/include#check-brands"
    categories = (HacsCategory.INTEGRATION,)

    async def async_validate(self) -> None:
        """Validate the repository."""
        
        # Check for local brand icons first (HA 2026.3.0+)
        domain = self.repository.data.domain
        local_icon_path = f"custom_components/{domain}/brand/icon.png"
        
        # Check if local brand icon exists in repository tree
        has_local_icon = any(
            file.filename == local_icon_path 
            for file in self.repository.tree
        )
        
        if has_local_icon:
            # Local brand icons found, validation passes
            return

        # No local icons, check brands repo as fallback
        response = await self.hacs.session.get(URL)
        content = await response.json()

        if self.repository.data.domain not in content["custom"]:
            raise ValidationException(
                f"The repository must either have local brand icons "
                f"(custom_components/{domain}/brand/icon.png) or be added to the brands repo"
            )
