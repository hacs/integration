from typing import Generator

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
import pytest

from custom_components.hacs.const import DOMAIN

from tests.common import (
    CategoryTestData,
    WSClient,
    category_test_data_parametrized,
    get_hacs,
)
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize("category_test_data", category_test_data_parametrized())
async def test_update_repository_entity(
    hass: HomeAssistant,
    setup_integration: Generator,
    category_test_data: CategoryTestData,
    snapshots: SnapshotFixture,
):
    hacs = get_hacs(hass)
    repo = hacs.repositories.get_by_full_name(category_test_data["repository"])

    assert repo is not None

    repo.data.installed = True
    repo.data.installed_version = category_test_data["version_base"]

    await hass.config_entries.async_reload(hacs.configuration.config_entry.entry_id)
    await hass.async_block_till_done()

    # Get a new HACS instance after reload
    hacs = get_hacs(hass)

    er = async_get_entity_registry(hacs.hass)

    entity_id = er.async_get_entity_id("update", DOMAIN, repo.data.id)

    await hass.services.async_call(
        "update",
        "install",
        service_data={"entity_id": entity_id, "version": category_test_data["version_update"]},
        blocking=True,
    )
    assert repo.data.installed_version == category_test_data["version_update"]

    await snapshots.assert_hacs_data(
        hacs, f"{category_test_data['repository']}/test_update_repository_entity.json"
    )

    # cleanup
    repo.data.installed = False


@pytest.mark.parametrize("category_test_data", category_test_data_parametrized())
async def test_update_repository_websocket(
    hass: HomeAssistant,
    setup_integration: Generator,
    ws_client: WSClient,
    category_test_data: CategoryTestData,
    snapshots: SnapshotFixture,
):
    hacs = get_hacs(hass)
    repo = hacs.repositories.get_by_full_name(category_test_data["repository"])

    assert repo is not None

    repo.data.installed = True
    repo.data.installed_version = category_test_data["version_base"]

    response = await ws_client.send_and_receive_json(
        "hacs/repository/download",
        {"repository": repo.data.id, "version": category_test_data["version_update"]},
    )
    assert response["success"] == True
    assert repo.data.installed_version == category_test_data["version_update"]

    await snapshots.assert_hacs_data(
        hacs, f"{category_test_data['repository']}/test_update_repository_websocket.json"
    )

    # cleanup
    repo.data.installed = False
