"""Test update entity."""

from collections.abc import Generator
import json as json_func
import os

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
import pytest

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
async def test_update_entity_state(
    time_freezer: FrozenDateTimeFactory,
    hass: HomeAssistant,
    response_mocker: ResponseMocker,
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

    # Get initial state
    state = hass.states.get(entity_id)
    initial_state = recursive_remove_key(
        state.as_dict(), ("id", "last_changed", "last_reported", "last_updated",
                          "display_precision", "update_percentage"),
    )

    # Bump version
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
        repo_data["last_version"] = "2.0.0"

    response_mocker.add(
        f"https://data-v2.hacs.xyz/{category_test_data['category']}/data.json",
        MockedResponse(content=data),
    )

    repo = hacs.repositories.get_by_full_name(category_test_data["repository"])

    time_freezer.tick(3600 * 48 + 1)
    await hass.async_block_till_done()
    await hass.async_block_till_done()

    # Get updated state
    state = hass.states.get(entity_id)
    updated_state = recursive_remove_key(
        state.as_dict(), ("id", "last_changed", "last_reported", "last_updated",
                          "display_precision", "update_percentage"),
    )

    snapshots.assert_match(
        safe_json_dumps({"initial_state": initial_state,
                        "updated_state": updated_state}),
        f"{category_test_data['repository']}/test_update_entity_state.json",
    )
