import pytest

from custom_components.hacs.checks.common.repository_topics import RepositoryTopics
from tests.dummy_repository import dummy_repository_base


@pytest.mark.asyncio
async def test_repository_no_topics():
    repository = dummy_repository_base()
    repository.data.topics = []
    check = RepositoryTopics(repository)
    await check._async_run_check()
    assert check.failed


@pytest.mark.asyncio
async def test_repository_hacs_topics():
    repository = dummy_repository_base()
    repository.data.topics = ["test"]
    check = RepositoryTopics(repository)
    await check._async_run_check()
    assert not check.failed
