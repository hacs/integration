from pathlib import Path

from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.hacs.base import HacsBase
from custom_components.hacs.const import DOMAIN

from tests.common import WSClient


def test_pinned(hacs: HacsBase):
    repository = hacs.repositories.get_by_full_name("hacs-test-org/integration-basic")
    registry = er.async_get(hacs.hass)

    assert repository.pinned is False

    repository.data.installed = True
    assert repository.pinned is False

    entry = registry.async_get_or_create("update", DOMAIN, str(repository.data.id))
    assert repository.pinned is False

    registry.async_update_entity(entry.entity_id, disabled_by=er.RegistryEntryDisabler.USER)
    assert repository.pinned is True


async def test_pinned_websocket(hacs: HacsBase, ws_client: WSClient):
    repository = hacs.repositories.get_by_full_name("hacs-test-org/integration-basic")
    repository.data.installed = True
    er.async_get(hacs.hass).async_get_or_create(
        "update",
        DOMAIN,
        str(repository.data.id),
        disabled_by=er.RegistryEntryDisabler.USER,
    )

    response = await ws_client.send_and_receive_json("hacs/repositories/list", {})
    listed = next(
        entry for entry in response["result"] if entry["full_name"] == repository.data.full_name
    )
    assert listed["pinned"] is True

    response = await ws_client.send_and_receive_json(
        "hacs/repository/info",
        {"repository_id": repository.data.id},
    )
    assert response["result"]["pinned"] is True


async def test_pinned_cleared_on_remove(hacs: HacsBase, ws_client: WSClient):
    repository = hacs.repositories.get_by_full_name("hacs-test-org/integration-basic")
    repository.data.installed = True
    config_entry = hacs.configuration.config_entry
    device = dr.async_get(hacs.hass).async_get_or_create(
        config_entry_id=config_entry.entry_id, identifiers={(DOMAIN, str(repository.data.id))},
    )
    registry = er.async_get(hacs.hass)
    registry.async_get_or_create(
        "update",
        DOMAIN,
        str(repository.data.id),
        config_entry=config_entry,
        device_id=device.id,
        disabled_by=er.RegistryEntryDisabler.USER,
    )

    # workaround for local path bug in tests
    repository.content.path.local = repository.localpath
    Path(repository.localpath).mkdir(parents=True, exist_ok=True)

    response = await ws_client.send_and_receive_json(
        "hacs/repository/remove", {"repository": repository.data.id},
    )
    assert response["success"] is True

    entry = registry.async_get_or_create(
        "update", DOMAIN, str(repository.data.id), config_entry=config_entry,
    )
    assert entry.disabled_by is None
