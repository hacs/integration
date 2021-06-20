# pylint: disable=missing-module-docstring, missing-function-docstring
import pytest

from custom_components.hacs.enums import HacsStage


@pytest.mark.asyncio
async def test_hacs(hacs, repository, tmpdir):
    hacs.hass.config.config_dir = tmpdir

    hacs.set_repositories([])
    assert hacs.get_repository(repository_id=None) is None

    repository.data.id = "1337"

    hacs.set_repositories([repository])
    assert hacs.get_repository(repository_id="1337").data.full_name == "test/test"
    assert hacs.get_repository(repository_id="1337").data.full_name_lower == "test/test"

    hacs.set_repositories([])
    assert hacs.get_repository(repository_name=None) is None

    hacs.set_repositories([repository])
    assert hacs.get_repository(repository_name="test/test").data.id == "1337"
    assert hacs.is_known("1337")

    await hacs.prosess_queue()
    await hacs.clear_out_removed_repositories()


@pytest.mark.asyncio
async def test_add_remove_repository(hacs, repository, tmpdir):
    hacs.hass.config.config_dir = tmpdir

    repository.data.id = "0"
    hacs.add_repository(repository)

    hacs.async_set_repository_id(repository, "42")

    # Once its set, it should never change
    with pytest.raises(ValueError):
        hacs.async_set_repository_id(repository, "30")

    # Safe to set it again
    hacs.async_set_repository_id(repository, "42")

    assert hacs.get_repository(repository_name="test/test") is repository
    assert hacs.get_repository(repository_id="42") is repository

    hacs.remove_repository(repository)
    assert hacs.get_repository(repository_name="test/test") is None
    assert hacs.get_repository(repository_id="42") is None

    # Verify second removal does not raise
    hacs.remove_repository(repository)


@pytest.mark.asyncio
async def test_set_stage(hacs):
    assert hacs.stage == HacsStage.SETUP
    hacs.set_stage(HacsStage.RUNNING)
    assert hacs.stage == HacsStage.RUNNING
