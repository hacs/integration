"""Test the diagnostics module."""

from custom_components.hacs.base import HacsBase
from custom_components.hacs.diagnostics import async_get_config_entry_diagnostics

from tests.common import (
    TOKEN,
    MockedResponse,
    ResponseMocker,
    recursive_remove_key,
    safe_json_dumps,
)
from tests.conftest import SnapshotFixture

REMOVE_KEYS = ("entry_id", "last_updated", "local", "minor_version",
               "created_at", "modified_at", "discovery_keys")


async def test_diagnostics(hacs: HacsBase, snapshots: SnapshotFixture):
    """Test the base result."""
    diagnostics = await async_get_config_entry_diagnostics(
        hacs.hass,
        hacs.configuration.config_entry,
    )

    assert TOKEN not in str(diagnostics)
    snapshots.assert_match(
        safe_json_dumps(recursive_remove_key(
            diagnostics, REMOVE_KEYS)), "diagnostics/base.json"
    )


async def test_diagnostics_with_exception(
    hacs: HacsBase,
    snapshots: SnapshotFixture,
    response_mocker: ResponseMocker,
):
    """Test the result with issues getting the ratelimit."""
    response_mocker.add(
        "https://api.github.com/rate_limit",
        MockedResponse(status=400, content="Something went wrong"),
    )
    diagnostics = await async_get_config_entry_diagnostics(
        hacs.hass,
        hacs.configuration.config_entry,
    )

    snapshots.assert_match(
        safe_json_dumps(recursive_remove_key(diagnostics, REMOVE_KEYS)),
        "diagnostics/exception.json",
    )
