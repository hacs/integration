from __future__ import annotations

from typing import TYPE_CHECKING

from .base import ActionValidationBase, ValidationException

if TYPE_CHECKING:
    from ..repositories.base import HacsRepository

OPEN_SOURCE_LICENSES = {
    "agpl-3.0",
    "apache-2.0",
    "bsd-2-clause",
    "bsd-3-clause",
    "bsl-1.0",
    "cc0-1.0",
    "epl-2.0",
    "gpl-2.0",
    "gpl-3.0",
    "lgpl-2.1",
    "mit",
    "mpl-2.0",
    "unlicense",
}


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
        if license_info.get("key") not in OPEN_SOURCE_LICENSES:
            raise ValidationException(
                "The repository has no recognized open source license "
                f"(license key is '{license_info.get('key', 'unknown')}')"
            )
        self.repository.logger.debug(
            "The repository has a valid license: %s", license_info.get("name")
        )
