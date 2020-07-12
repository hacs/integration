import pytest

from homeassistant.core import HomeAssistant

from custom_components.hacs.share import get_hacs
from custom_components.hacs.repositories import HacsPlugin


class MockPackage:
    content = '{"author": "developer"}'


class MockRepositoryObject:
    async def get_contents(self, _path, ref_):
        return MockPackage()


@pytest.mark.asyncio
async def test_get_package_content():
    hacs = get_hacs()
    hacs.hass = HomeAssistant()
    repository = HacsPlugin("test/test")
    repository.hacs = hacs

    await repository.get_package_content()
    repository.repository_object = MockRepositoryObject()
    await repository.get_package_content()
