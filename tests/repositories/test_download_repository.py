import os

from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.enums import HacsCategory

from tests.common import get_hacs
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize(
    "category",
    ((HacsCategory.INTEGRATION), (HacsCategory.TEMPLATE)),
)
@pytest.mark.asyncio
async def test_download_repository(
    hass: HomeAssistant,
    setup_integration: HacsBase,
    category: HacsCategory,
    snapshots: SnapshotFixture,
):
    hacs = get_hacs(hass)
    full_name = f"octocat/{category.value}"

    repo = hacs.repositories.get_by_full_name(full_name)
    assert repo is not None
    assert repo.data.installed is False

    assert not os.path.isdir(repo.localpath)

    assert len(hacs.repositories.list_downloaded) == 1

    await repo.async_install()

    assert len(hacs.repositories.list_downloaded) == 2

    assert repo.data.installed is True
    assert os.path.isdir(repo.localpath)

    await snapshots.assert_hacs_data(hacs, f"{category.value}_test_download_repository.json")
