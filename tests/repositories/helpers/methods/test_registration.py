import pytest

from tests.dummy_repository import dummy_repository_integration


@pytest.mark.asyncio
async def test_registration(hass, aresponses, event_loop):
    repository = dummy_repository_integration(hass)
    await repository.async_pre_registration()
    await repository.async_post_registration()
