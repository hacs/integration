import pytest

from custom_components.hacs.exceptions import HacsException


@pytest.mark.asyncio
async def test_base(repository_appdaemon):
    assert repository_appdaemon.data.category == "appdaemon"


@pytest.mark.asyncio
async def test_validate_repository(repository_appdaemon):
    with pytest.raises(HacsException):
        await repository_appdaemon.validate_repository()


@pytest.mark.asyncio
async def test_update_repository(repository_appdaemon):
    await repository_appdaemon.update_repository()
