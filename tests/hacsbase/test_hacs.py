# pylint: disable=missing-module-docstring, missing-function-docstring
import pytest

from custom_components.hacs.base import HacsRepositories
from custom_components.hacs.enums import HacsStage


@pytest.mark.asyncio
async def test_hacs(hacs, repository, tmpdir):
    hacs.hass.config.config_dir = tmpdir

    hacs.repositories = HacsRepositories()
    assert hacs.repositories.get_by_id(None) is None

    repository.data.id = "1337"

    hacs.repositories.register(repository)
    assert hacs.repositories.get_by_id("1337").data.full_name == "test/test"
    assert hacs.repositories.get_by_id("1337").data.full_name_lower == "test/test"

    hacs.repositories = HacsRepositories()
    assert hacs.repositories.get_by_full_name(None) is None

    hacs.repositories.register(repository)
    assert hacs.repositories.get_by_full_name("test/test").data.id == "1337"
    assert hacs.repositories.is_registered(repository_id="1337")

    if queue_task := hacs.tasks.get("prosess_queue"):
        await queue_task.execute_task()
    await hacs.clear_out_removed_repositories()


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_set_stage(hacs):
    assert hacs.stage == None
    await hacs.async_set_stage(HacsStage.RUNNING)
    assert hacs.stage == HacsStage.RUNNING
