import pytest

from custom_components.hacs.validate.description import Validator


@pytest.mark.asyncio
async def test_repository_no_description(repository):
    repository.data.description = ""
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


@pytest.mark.asyncio
async def test_repository_hacs_description(repository):
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed
