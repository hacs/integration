from __future__ import annotations

from ..repositories.base import HacsRepository
from .base import ActionValidationBase, ValidationException


async def async_setup_validator(repository: HacsRepository) -> Validator:
    """Set up this validator."""
    return Validator(repository=repository)


class Validator(ActionValidationBase):
    """Validate the repository."""

    more_info = "https://hacs.xyz/docs/publish/include#check-archived"
    allow_fork = False

    async def async_validate(self):
        """Validate the repository."""
        if self.repository.data.archived:
            raise ValidationException("The repository is archived")
