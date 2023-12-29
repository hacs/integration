from typing import Generator

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
import pytest

from custom_components.hacs.const import DOMAIN

from tests.common import WSClient, get_hacs
from tests.conftest import SnapshotFixture

test_data = (
    ("hacs-test-org/appdaemon-basic", "1.0.0", "2.0.0"),
    ("hacs-test-org/integration-basic", "1.0.0", "2.0.0"),
    ("hacs-test-org/plugin-basic", "1.0.0", "2.0.0"),
    ("hacs-test-org/template-basic", "1.0.0", "2.0.0"),
    ("hacs-test-org/theme-basic", "1.0.0", "2.0.0"),
)


@pytest.mark.parametrize(
    "repository_full_name,from_version,to_version",
    test_data,
)
async def test_update_repository_entity(
    hass: HomeAssistant,
    setup_integration: Generator,
    repository_full_name: str,
    from_version: str,
    to_version: str,
    snapshots: SnapshotFixture,
):
    hacs = get_hacs(hass)
    repo = hacs.repositories.get_by_full_name(repository_full_name)

    assert repo is not None

    repo.data.installed = True
    repo.data.installed_version = from_version

    await hass.config_entries.async_reload(hacs.configuration.config_entry.entry_id)
    await hass.async_block_till_done()

    # Get a new HACS instance after reload
    hacs = get_hacs(hass)

    er = async_get_entity_registry(hacs.hass)

    entity_id = er.async_get_entity_id("update", DOMAIN, repo.data.id)

    await hass.services.async_call(
        "update",
        "install",
        service_data={"entity_id": entity_id, "version": to_version},
        blocking=True,
    )
    assert repo.data.installed_version == to_version

    await snapshots.assert_hacs_data(
        hacs, f"{repository_full_name}/test_update_repository_entity.json"
    )


@pytest.mark.parametrize(
    "repository_full_name,from_version,to_version",
    test_data,
)
async def test_update_repository_websocket(
    hass: HomeAssistant,
    setup_integration: Generator,
    ws_client: WSClient,
    repository_full_name: str,
    from_version: str,
    to_version: str,
    snapshots: SnapshotFixture,
):
    hacs = get_hacs(hass)
    repo = hacs.repositories.get_by_full_name(repository_full_name)

    assert repo is not None

    repo.data.installed = True
    repo.data.installed_version = from_version

    response = await ws_client.send_and_receive_json(
        "hacs/repository/download", {"repository": repo.data.id, "version": to_version}
    )
    assert response["success"] == True
    assert repo.data.installed_version == to_version

    await snapshots.assert_hacs_data(
        hacs, f"{repository_full_name}/test_update_repository_websocket.json"
    )
