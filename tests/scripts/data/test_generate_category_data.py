"""Test generate category data."""
import json

from homeassistant.core import HomeAssistant

from scripts.data.generate_category_data import OUTPUT_DIR, generate_category_data

from tests.common import (
    MockedResponse,
    ResponseMocker,
    recursive_remove_key,
    safe_json_dumps,
)
from tests.conftest import SnapshotFixture

BASE_HEADERS = {"Content-Type": "application/json"}
RATE_LIMIT_HEADER = {
    **BASE_HEADERS,
    "X-RateLimit-Limit": "9999",
    "X-RateLimit-Remaining": "9999",
    "X-RateLimit-Reset": "9999",
}


async def test_generate_category_data_single_repository(
    hass: HomeAssistant,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
):
    """Test behaviour if single repository."""
    response_mocker.add(
        "https://data-v2.hacs.xyz/integration/data.json", MockedResponse(content={})
    )
    await generate_category_data("integration", "hacs-test-org/integration-basic")

    with open(f"{OUTPUT_DIR}/integration/data.json", encoding="utf-8") as file:
        snapshots.assert_match(
            safe_json_dumps(recursive_remove_key(json.loads(file.read()), ("last_fetched",))),
            "scripts/data/generate_category_data/single/data.json",
        )

    with open(f"{OUTPUT_DIR}/integration/repositories.json", encoding="utf-8") as file:
        snapshots.assert_match(
            safe_json_dumps(json.loads(file.read())),
            "scripts/data/generate_category_data/single/repositories.json",
        )
