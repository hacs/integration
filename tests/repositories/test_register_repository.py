from typing import Generator

from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs.enums import HacsCategory

from tests.common import WSClient, get_hacs, recursive_remove_key, safe_json_dumps
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize(
    "repository_full_name,category",
    (("hacs-test-org/integration-basic-custom", HacsCategory.INTEGRATION),),
)
@pytest.mark.asyncio
async def test_register_repository(
    hass: HomeAssistant,
    setup_integration: Generator,
    repository_full_name: str,
    category: HacsCategory,
    snapshots: SnapshotFixture,
    ws_client: WSClient,
):
    hacs = get_hacs(hass)

    assert hacs.repositories.get_by_full_name(repository_full_name) is None

    response = await ws_client.send_and_receive_json(
        "hacs/repositories/add", {"repository": repository_full_name, "category": category.value}
    )
    assert response["success"] == True
    repo = hacs.repositories.get_by_full_name(repository_full_name)
    assert repo is not None

    response = await ws_client.send_and_receive_json(
        "hacs/repository/info", {"repository_id": repo.data.id}
    )
    assert response["success"] == True

    snapshots.assert_match(
        safe_json_dumps(recursive_remove_key(response["result"], ("last_updated", "local_path"))),
        f"{repository_full_name}/test_register_repository.json",
    )
