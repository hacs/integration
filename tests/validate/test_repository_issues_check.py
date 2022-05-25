import pytest

from custom_components.hacs.validate.issues import Validator


@pytest.mark.asyncio
async def test_repository_issues_enabled(repository):
    repository.data.has_issues = True
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


@pytest.mark.asyncio
async def test_repository_issues_not_enabled(repository):
    repository.data.has_issues = False
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed
