import pytest


@pytest.mark.asyncio
async def test_reinstall_if_needed(repository):
    repository.content.path.local = "/non/existing/dir"
    repository.data.installed = True
    await repository.async_reinstall_if_needed()
