from __future__ import annotations

from ..repositories.base import HacsRepository
from .base import ActionValidationBase, ValidationException


async def async_setup_validator(repository: HacsRepository) -> Validator:
    """Set up this validator."""
    return Validator(repository=repository)


class Validator(ActionValidationBase):
    """Validate the repository."""

    async def async_validate(self):
        """Validate the repository."""
        if not self.repository.data.topics:
            raise ValidationException("The repository has no topics")
