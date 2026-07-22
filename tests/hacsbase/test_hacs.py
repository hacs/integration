# pylint: disable=missing-module-docstring, missing-function-docstring
import pytest

from custom_components.hacs.base import HacsRepositories
from custom_components.hacs.enums import HacsCategory
from custom_components.hacs.repositories.base import HacsRepository


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


async def test_register_renamed_repository(hacs, repository, tmpdir):
    """Registering a known id under a new name must update the name index."""
    hacs.hass.config.config_dir = tmpdir

    hacs.repositories = HacsRepositories()

    repository.data.id = "1337"
    hacs.repositories.register(repository, True)

    renamed = HacsRepository(hacs)
    renamed.data.id = "1337"
    renamed.data.full_name = "test/renamed"

    hacs.repositories.register(renamed)

    assert repository.data.full_name == "test/renamed"
    assert repository.data.full_name_lower == "test/renamed"
    assert hacs.repositories.get_by_full_name("test/renamed") is repository
    assert hacs.repositories.get_by_full_name("test/test") is None
    assert hacs.repositories.get_by_id("1337") is repository

    # The repository keeps its default status through the rename
    assert hacs.repositories.is_default("1337")


async def test_rename_repository(hacs, repository, tmpdir):
    """Renaming a repository keeps the name index in sync."""
    hacs.hass.config.config_dir = tmpdir

    hacs.repositories = HacsRepositories()

    repository.data.id = "1337"
    hacs.repositories.register(repository)

    hacs.repositories.rename(repository, "Test/Renamed")

    assert repository.data.full_name == "Test/Renamed"
    assert repository.data.full_name_lower == "test/renamed"
    assert hacs.repositories.get_by_full_name("Test/Renamed") is repository
    assert hacs.repositories.get_by_full_name("test/renamed") is repository
    assert hacs.repositories.get_by_full_name("test/test") is None
