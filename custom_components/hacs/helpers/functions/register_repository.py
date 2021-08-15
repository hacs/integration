"""Register a repository."""
from __future__ import annotations

from typing import TYPE_CHECKING

from aiogithubapi import AIOGitHubAPIException

from custom_components.hacs.helpers.classes.exceptions import (
    HacsException,
    HacsExpectedException,
    HacsRepositoryExistException,
)
from custom_components.hacs.share import get_hacs

from ...repositories import RERPOSITORY_CLASSES

if TYPE_CHECKING:
    from ..classes.repository import HacsRepository

# @concurrent(15, 5)
async def register_repository(full_name, category, check=True, ref=None):
    """Register a repository."""
    hacs = get_hacs()

    if full_name in hacs.common.skip:
        if full_name != "hacs/integration":
            raise HacsExpectedException(f"Skipping {full_name}")

    if category not in RERPOSITORY_CLASSES:
        raise HacsException(f"{category} is not a valid repository category.")

    repository: HacsRepository = RERPOSITORY_CLASSES[category](full_name)
    if check:
        try:
            await repository.async_registration(ref)
            if hacs.status.new:
                repository.data.new = False
            if repository.validate.errors:
                hacs.common.skip.append(repository.data.full_name)
                if not hacs.status.startup:
                    hacs.log.error("Validation for %s failed.", full_name)
                if hacs.system.action:
                    raise HacsException(f"::error:: Validation for {full_name} failed.")
                return repository.validate.errors
            if hacs.system.action:
                repository.logger.info("%s Validation completed", repository)
            else:
                repository.logger.info("%s Registration completed", repository)
        except HacsRepositoryExistException:
            return
        except AIOGitHubAPIException as exception:
            hacs.common.skip.append(repository.data.full_name)
            raise HacsException(
                f"Validation for {full_name} failed with {exception}."
            ) from None

    if str(repository.data.id) != "0" and (
        exists := hacs.get_by_id(repository.data.id)
    ):
        hacs.async_remove_repository(exists)

    else:
        if hacs.hass is not None and (
            (check and repository.data.new) or hacs.status.new
        ):
            hacs.hass.bus.async_fire(
                "hacs/repository",
                {
                    "action": "registration",
                    "repository": repository.data.full_name,
                    "repository_id": repository.data.id,
                },
            )
    hacs.async_add_repository(repository)
