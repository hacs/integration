# pylint: disable=missing-module-docstring, missing-function-docstring
import pytest

from custom_components.hacs.base import HacsRepositories
from custom_components.hacs.enums import HacsCategory


async def test_hacs(hacs, repository, tmpdir):
    hacs.hass.config.config_dir = tmpdir

    hacs.repositories = HacsRepositories()
    assert hacs.repositories.get_by_id(None) is None

    repository.data.id = "1337"
    repository.data.category = "integration"
    repository.data.installed = True

    hacs.repositories.register(repository)
    assert hacs.repositories.get_by_id("1337").data.full_name == "test/test"
    assert hacs.repositories.get_by_id("1337").data.full_name_lower == "test/test"

    hacs.repositories = HacsRepositories()
    assert hacs.repositories.get_by_full_name(None) is None

    hacs.repositories.register(repository)
    assert hacs.repositories.get_by_full_name("test/test").data.id == "1337"
    assert hacs.repositories.is_registered(repository_id="1337")

    assert hacs.repositories.category_downloaded(category=HacsCategory.INTEGRATION)
    for category in [x for x in list(HacsCategory) if x != HacsCategory.INTEGRATION]:
        assert not hacs.repositories.category_downloaded(category=category)

    await hacs.async_process_queue()


async def test_add_remove_repository(hacs, repository, tmpdir):
    hacs.hass.config.config_dir = tmpdir

    repository.data.id = "0"
    hacs.repositories.register(repository)

    hacs.repositories.set_repository_id(repository, "42")

    # Once its set, it should never change
    with pytest.raises(ValueError):
        hacs.repositories.set_repository_id(repository, "30")

    # Safe to set it again
    hacs.repositories.set_repository_id(repository, "42")

    assert hacs.repositories.get_by_full_name("test/test") is repository
    assert hacs.repositories.get_by_id("42") is repository

    hacs.repositories.unregister(repository)
    assert hacs.repositories.get_by_full_name("test/test") is None
    assert hacs.repositories.get_by_id("42") is None

    # Verify second removal does not raise
    hacs.repositories.unregister(repository)
