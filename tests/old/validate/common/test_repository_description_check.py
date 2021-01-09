import pytest

from custom_components.hacs.validate.common.repository_description import (
    RepositoryDescription,
)


@pytest.mark.asyncio
async def test_repository_no_description(repository):
    repository.data.description = ""
    check = RepositoryDescription(repository)
    await check._async_run_check()
    assert check.failed


@pytest.mark.asyncio
async def test_repository_hacs_description(repository):
    check = RepositoryDescription(repository)
    await check._async_run_check()
    assert not check.failed
