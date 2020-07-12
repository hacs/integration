import pytest
from homeassistant.core import HomeAssistant
from custom_components.hacs.hacsbase.hacs import Hacs

from tests.dummy_repository import dummy_repository_base


@pytest.mark.asyncio
async def test_hacs(tmpdir):
    hacs = Hacs()
    hacs.hass = HomeAssistant()
    hacs.hass.config.config_dir = tmpdir

    hacs.repositories = [None]
    assert hacs.get_by_id(None) is None

    repo = dummy_repository_base()
    repo.data.id = "1337"

    hacs.repositories = [repo]
    assert hacs.get_by_id("1337").data.full_name == "test/test"

    hacs.repositories = [None]
    assert hacs.get_by_name(None) is None

    hacs.repositories = [repo]
    assert hacs.get_by_name("test/test").data.id == "1337"

    assert hacs.is_known("1337")

    hacs.sorted_by_name
    hacs.sorted_by_repository_name

    await hacs.prosess_queue()
    await hacs.clear_out_removed_repositories()
