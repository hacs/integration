"""Register a repository."""
from aiogithubapi import AIOGitHubException
from custom_components.hacs.globals import get_hacs
from custom_components.hacs.hacsbase.exceptions import (
    HacsException,
    HacsExpectedException,
)


async def register_repository(full_name, category, check=True):
    """Register a repository."""
    hacs = get_hacs()
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
            await repository.registration()
            if hacs.system.status.new:
                repository.status.new = False
            if repository.validate.errors:
                hacs.common.skip.append(repository.data.full_name)
                if not hacs.system.status.startup:
                    hacs.logger.error(f"Validation for {full_name} failed.")
                return repository.validate.errors
            repository.logger.info("Registration complete")
        except AIOGitHubException as exception:
            hacs.common.skip.append(repository.data.full_name)
            raise HacsException(f"Validation for {full_name} failed with {exception}.")

    hacs.hass.bus.async_fire(
        "hacs/repository",
        {
            "id": 1337,
            "action": "registration",
            "repository": repository.data.full_name,
            "repository_id": repository.information.uid,
        },
    )
    hacs.repositories.append(repository)
