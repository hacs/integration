"""Register a repository."""
from aiogithubapi import AIOGitHubAPIException
from custom_components.hacs.globals import get_hacs
from custom_components.hacs.hacsbase.exceptions import (
    HacsException,
    HacsExpectedException,
)
from queueman import concurrent


# @concurrent(15, 5)
async def register_repository(full_name, category, check=True, ref=None, action=False):
    """Register a repository."""
    hacs = get_hacs()
    hacs.action = action
    from custom_components.hacs.repositories import (
        RERPOSITORY_CLASSES,
    )  # To hanle import error

    if full_name in hacs.common.skip:
        if full_name != "hacs/integration":
            raise HacsExpectedException(f"Skipping {full_name}")

    if category not in RERPOSITORY_CLASSES:
        raise HacsException(f"{category} is not a valid repository category.")

    repository = RERPOSITORY_CLASSES[category](full_name)
    if check:
        try:
            await repository.registration(ref)
            if hacs.system.status.new:
                repository.data.new = False
            if repository.validate.errors:
                hacs.common.skip.append(repository.data.full_name)
                if not hacs.system.status.startup:
                    hacs.logger.error(f"Validation for {full_name} failed.")
                if hacs.action:
                    raise HacsException(f"Validation for {full_name} failed.")
                return repository.validate.errors
            if hacs.action:
                repository.logger.info("Validation complete")
            else:
                repository.logger.info("Registration complete")
        except AIOGitHubAPIException as exception:
            hacs.common.skip.append(repository.data.full_name)
            raise HacsException(f"Validation for {full_name} failed with {exception}.")

    exists = (
        False
        if str(repository.data.id) == "0"
        else [x for x in hacs.repositories if str(x.data.id) == str(repository.data.id)]
    )

    if exists:
        if exists[0] in hacs.repositories:
            hacs.repositories.remove(exists[0])

    else:
        if hacs.hass is not None:
            hacs.hass.bus.async_fire(
                "hacs/repository",
                {
                    "id": 1337,
                    "action": "registration",
                    "repository": repository.data.full_name,
                    "repository_id": repository.data.id,
                },
            )
    hacs.repositories.append(repository)
