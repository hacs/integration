from collections.abc import Generator

from homeassistant.core import HomeAssistant
import pytest

from tests.common import (
    CategoryTestData,
    MockedResponse,
    ResponseMocker,
    WSClient,
    category_test_data_parametrized,
    get_hacs,
    safe_json_dumps,
)
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize("category_test_data", category_test_data_parametrized())
async def test_get_reposiotry_releases(
    hass: HomeAssistant,
    setup_integration: Generator,
    response_mocker: ResponseMocker,
    ws_client: WSClient,
    category_test_data: CategoryTestData,
    snapshots: SnapshotFixture,
):
    hacs = get_hacs(hass)

    repo = hacs.repositories.get_by_full_name(category_test_data["repository"])
    assert repo is not None

    response_mocker.add(
        "https://api.github.com/graphql",
        response=MockedResponse(
            content={
                "data": {
                    "repository": {
                        "releases": {
                            "nodes": [
                                {
                                    "name": category_test_data["version_update"],
                                    "publishedAt": "2019-02-26T15:02:39Z",
                                    "tagName": category_test_data["version_update"],
                                    "isPrerelease": False,
                                }
                            ]
                        }
                    }
                }
            }
        ),
    )

    response = await ws_client.send_and_receive_json(
        "hacs/repository/releases",
        {"repository_id": repo.data.id},
    )
    assert response["success"] == True

    snapshots.assert_match(
        safe_json_dumps(response),
        f"{category_test_data['repository']
           }/test_get_reposiotry_releases.json",
    )
