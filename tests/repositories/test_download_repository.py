from typing import Generator

from homeassistant.core import HomeAssistant
import pytest

from tests.common import WSClient, get_hacs
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize(
    "repository_full_name",
    (("hacs-test-org/integration-basic"), ("hacs-test-org/template-basic"),("hacs-test-org/plugin-basic")),
)
@pytest.mark.asyncio
async def test_download_repository(
    hass: HomeAssistant,
    setup_integration: Generator,
    ws_client: WSClient,
    repository_full_name: str,
    snapshots: SnapshotFixture,
):
    hacs = get_hacs(hass)

    repo = hacs.repositories.get_by_full_name(repository_full_name)
    assert repo is not None
    assert repo.data.installed is False

    assert len(hacs.repositories.list_downloaded) == 1

    response = await ws_client.send_and_receive_json(
        "hacs/repository/download", {"repository": repo.data.id}
    )
    assert response["success"] == True

    assert len(hacs.repositories.list_downloaded) == 2

    assert repo.data.installed is True

    await snapshots.assert_hacs_data(hacs, f"{repository_full_name}/test_download_repository.json")
