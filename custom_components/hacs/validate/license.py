from __future__ import annotations

from typing import TYPE_CHECKING

from .base import ActionValidationBase, ValidationException

if TYPE_CHECKING:
    from ..repositories.base import HacsRepository


async def async_setup_validator(repository: HacsRepository) -> Validator:
    """Set up this validator."""
    return Validator(repository=repository)


class Validator(ActionValidationBase):
    """Validate the repository."""

    more_info = "https://hacs.xyz/docs/publish/include#check-repository"
    allow_fork = False

    async def async_validate(self) -> None:
        """Validate the repository."""
        if (license_info := self.repository.repository_object.attributes.get("license")) is None:
            raise ValidationException("The repository has no license")
        if license_info.get("key") == "other":
            raise ValidationException(
                "The repository has no recognized license "
                f"(license name is '{license_info.get('name', 'unknown')}')"
            )
        self.repository.logger.debug(
            "The repository has a valid license: %s", license_info.get("name")
        )
