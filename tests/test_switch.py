"""Test switch entity."""

from collections.abc import Generator
import json as json_func
import os

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
import pytest

from custom_components.hacs import PLATFORMS
from custom_components.hacs.const import DOMAIN

from tests.common import (
    CategoryTestData,
    MockedResponse,
    ResponseMocker,
    category_test_data_parametrized,
    get_hacs,
    recursive_remove_key,
    safe_json_dumps,
)
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize("category_test_data", category_test_data_parametrized())
async def test_switch_entity_state(
    hass: HomeAssistant,
    setup_integration: Generator,
    response_mocker: ResponseMocker,
    category_test_data: CategoryTestData,
    snapshots: SnapshotFixture,
):
    hacs = get_hacs(hass)
    repo = hacs.repositories.get_by_full_name(category_test_data["repository"])

    states = {key: {} for key in PLATFORMS}

    assert repo is not None

    repo.data.installed = True
    repo.data.installed_version = category_test_data["version_base"]

    er = async_get_entity_registry(hass)
    await hass.config_entries.async_reload(hacs.configuration.config_entry.entry_id)
    await hass.async_block_till_done()

    fixture_file = f"fixtures/proxy/data-v2.hacs.xyz/{
        category_test_data['category']}/data.json"
    fp = os.path.join(
        os.path.dirname(__file__),
        fixture_file,
    )
    with open(fp, encoding="utf-8") as fptr:
        data = json_func.loads(fptr.read())

    for repo_data in data.values():
        repo_data["last_fetched"] += 1
        repo_data["last_version"] = category_test_data["version_update"]
        repo_data["prerelease"] = category_test_data["prerelease"]

    response_mocker.add(
        f"https://data-v2.hacs.xyz/{category_test_data['category']}/data.json",
        MockedResponse(content=data),
    )

    er.async_update_entity(er.async_get_entity_id(
        "switch", DOMAIN, repo.data.id), disabled_by=None)
    await hass.config_entries.async_reload(hacs.configuration.config_entry.entry_id)
    await hass.async_block_till_done()

    # Get a new HACS instance after reload
    hacs = get_hacs(hass)

    for platform in PLATFORMS:
        entity_id = er.async_get_entity_id(platform, DOMAIN, repo.data.id)
        assert entity_id is not None

        states[platform]["initial"] = recursive_remove_key(
            hass.states.get(entity_id).as_dict(),
            ("id", "last_changed", "last_reported", "last_updated",
             "display_precision", "update_percentage"),
        )

    await hass.services.async_call(
        domain="switch",
        service="turn_on",
        service_data={"entity_id": er.async_get_entity_id(
            "switch", DOMAIN, repo.data.id)},
        blocking=True,
    )

    for platform in PLATFORMS:
        entity_id = er.async_get_entity_id(platform, DOMAIN, repo.data.id)
        assert entity_id is not None
        states[platform]["updated"] = recursive_remove_key(
            hass.states.get(entity_id).as_dict(),
            ("id", "last_changed", "last_reported", "last_updated",
             "display_precision", "update_percentage"),
        )

    snapshots.assert_match(
        safe_json_dumps(states),
        f"{category_test_data['repository']}/test_switch/entity_states.json",
    )
