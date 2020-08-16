import pytest


@pytest.mark.asyncio
async def test_registration(repository):
    await repository.async_pre_registration()
    await repository.async_post_registration()
