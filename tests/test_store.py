"""HACS Store Test Suite."""
# pylint: disable=missing-docstring
import pytest

from custom_components.hacs.helpers.functions.store import (
    async_load_from_store,
    async_save_to_store,
)

from tests.common import fixture


@pytest.mark.asyncio
async def test_storage(hass):
    data = fixture("stored_repositories.json")
    print(data)
    await async_save_to_store(hass, "repositories", data)

    repositories = await async_load_from_store(hass, "repositories")
    print(repositories)
    assert repositories["999999"]["name"] == "test1"

    repositories = await async_load_from_store(hass, "does_not_exist")
    assert not repositories
