"""Test generate category data."""
import json

from homeassistant.core import HomeAssistant
import pytest

from scripts.data.generate_category_data import OUTPUT_DIR, generate_category_data

from tests.common import (
    CategoryTestData,
    MockedResponse,
    ResponseMocker,
    category_test_data_parametrized,
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


@pytest.mark.parametrize("category_test_data", category_test_data_parametrized())
async def test_generate_category_data_single_repository(
    hass: HomeAssistant,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
    category_test_data: CategoryTestData,
):
    """Test behaviour if single repository."""
    response_mocker.add(
        f"https://data-v2.hacs.xyz/{category_test_data['category']}/data.json",
        MockedResponse(content={}),
    )
    await generate_category_data(category_test_data["category"], category_test_data["repository"])

    with open(f"{OUTPUT_DIR}/{category_test_data['category']}/data.json", encoding="utf-8") as file:
        snapshots.assert_match(
            safe_json_dumps(recursive_remove_key(json.loads(file.read()), ("last_fetched",))),
            f"scripts/data/generate_category_data/single/{category_test_data['category']}/{category_test_data['repository']}/data.json",
        )

    with open(
        f"{OUTPUT_DIR}/{category_test_data['category']}/repositories.json", encoding="utf-8"
    ) as file:
        snapshots.assert_match(
            safe_json_dumps(json.loads(file.read())),
            f"scripts/data/generate_category_data/single/{category_test_data['category']}/{category_test_data['repository']}/repositories.json",
        )


@pytest.mark.parametrize("category_test_data", category_test_data_parametrized())
async def test_generate_category_data(
    hass: HomeAssistant,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
    category_test_data: CategoryTestData,
):
    """Test behaviour if single repository."""
    response_mocker.add(
        f"https://data-v2.hacs.xyz/{category_test_data['category']}/data.json",
        MockedResponse(content={}),
    )
    await generate_category_data(category_test_data["category"])

    with open(f"{OUTPUT_DIR}/{category_test_data['category']}/data.json", encoding="utf-8") as file:
        snapshots.assert_match(
            safe_json_dumps(recursive_remove_key(json.loads(file.read()), ("last_fetched",))),
            f"scripts/data/generate_category_data/{category_test_data['category']}//data.json",
        )

    with open(
        f"{OUTPUT_DIR}/{category_test_data['category']}/repositories.json", encoding="utf-8"
    ) as file:
        snapshots.assert_match(
            safe_json_dumps(recursive_remove_key(json.loads(file.read()), ())),
            f"scripts/data/generate_category_data/{category_test_data['category']}/repositories.json",
        )
