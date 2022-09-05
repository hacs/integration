from __future__ import annotations

from ..enums import HacsCategory
from ..repositories.base import HacsRepository
from .base import ActionValidationBase, ValidationException

IGNORED = ["-shield", "img.shields.io", "buymeacoffee.com"]


async def async_setup_validator(repository: HacsRepository) -> Validator:
    """Set up this validator."""
    return Validator(repository=repository)


class Validator(ActionValidationBase):
    """Validate the repository."""

    categories = [HacsCategory.PLUGIN, HacsCategory.THEME]
    more_info = "https://hacs.xyz/docs/publish/include#check-images"

    async def async_validate(self):
        """Validate the repository."""
        info = await self.repository.async_get_info_file_contents()
        for line in info.split("\n"):
            if "<img" in line or "![" in line:
                if [ignore for ignore in IGNORED if ignore in line]:
                    continue
                return
        raise ValidationException("The repository does not have images in the Readme file")
