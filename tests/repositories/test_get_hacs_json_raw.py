import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.repositories.base import HacsRepository

from tests.common import ResponseMocker, client_session_proxy


@pytest.mark.parametrize("version,expected", [
    ("1.0.0", {"name": "Integration basic 1.0.0"}),
    ("99.99.99", None),
])
async def test_get_hacs_json_raw(
    hacs: HacsBase,
    version: str,
    expected: dict | None,
    response_mocker: ResponseMocker,
):
    repository = HacsRepository(hacs=hacs)
    repository.data.full_name = "hacs-test-org/integration-basic"

    hacs.session = await client_session_proxy(hacs.hass)
    manifest = await repository.get_hacs_json_raw(version=version)

    if expected is not None:
        assert manifest["name"] == expected["name"]
    else:
        assert manifest is None
