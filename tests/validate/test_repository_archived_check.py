import pytest

from custom_components.hacs.validate.archived import Validator


@pytest.mark.asyncio
async def test_repository_archived(repository):
    repository.data.archived = True
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


@pytest.mark.asyncio
async def test_repository_not_archived(repository):
    repository.data.archived = False
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed
