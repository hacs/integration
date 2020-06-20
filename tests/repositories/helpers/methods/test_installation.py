import pytest
from tests.dummy_repository import dummy_repository_integration


@pytest.mark.asyncio
async def test_installation(aresponses, event_loop):
    repository = dummy_repository_integration()
    await repository.async_pre_install()
    await repository.async_post_installation()
