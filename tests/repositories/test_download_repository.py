from collections.abc import Generator

from homeassistant.core import HomeAssistant
import pytest

from tests.common import (
    CategoryTestData,
    WSClient,
    category_test_data_parametrized,
    get_hacs,
)
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize("category_test_data", category_test_data_parametrized())
async def test_download_repository(
    hass: HomeAssistant,
    setup_integration: Generator,
    ws_client: WSClient,
    category_test_data: CategoryTestData,
    snapshots: SnapshotFixture,
):
    hacs = get_hacs(hass)

    repo = hacs.repositories.get_by_full_name(category_test_data["repository"])
    assert repo is not None
    assert repo.data.installed is False

    assert len(hacs.repositories.list_downloaded) == 1

    # workaround for local path bug in tests
    repo.content.path.local = repo.localpath

    response = await ws_client.send_and_receive_json(
        "hacs/repository/download", {"repository": repo.data.id},
    )
    assert response["success"] == True

    assert len(hacs.repositories.list_downloaded) == 2

    assert repo.data.installed is True

    await snapshots.assert_hacs_data(
        hacs, f"{category_test_data['repository']}/test_download_repository.json",
    )
