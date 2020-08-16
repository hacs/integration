import pytest


@pytest.mark.asyncio
async def test_hacs(hacs, repository, tmpdir):
    hacs.hass.config.config_dir = tmpdir

    hacs.repositories = [None]
    assert hacs.get_by_id(None) is None

    repository.data.id = "1337"

    hacs.repositories = [repository]
    assert hacs.get_by_id("1337").data.full_name == "test/test"
    assert hacs.get_by_id("1337").data.full_name_lower == "test/test"

    hacs.repositories = [None]
    assert hacs.get_by_name(None) is None

    hacs.repositories = [repository]
    assert hacs.get_by_name("test/test").data.id == "1337"

    assert hacs.is_known("1337")

    await hacs.prosess_queue()
    await hacs.clear_out_removed_repositories()
