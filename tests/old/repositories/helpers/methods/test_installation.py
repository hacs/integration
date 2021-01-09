import pytest


@pytest.mark.asyncio
async def test_installation(repository):
    await repository.async_pre_install()
    await repository.async_post_installation()
