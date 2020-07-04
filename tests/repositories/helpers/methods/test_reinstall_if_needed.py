import pytest

from tests.dummy_repository import dummy_repository_base


@pytest.mark.asyncio
async def test_reinstall_if_needed():
    repository = dummy_repository_base()
    repository.content.path.local = "/non/existing/dir"
    repository.data.installed = True
    await repository.async_reinstall_if_needed()
