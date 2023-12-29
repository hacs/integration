import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.repositories.base import HacsRepository

from tests.common import ResponseMocker, client_session_proxy


@pytest.mark.parametrize("version,name", [("1.0.0", "Integration basic 1.0.0"), ("99.99.99", None)])
async def test_validate_repository(
    hacs: HacsBase,
    version: str,
    name: str | None,
    response_mocker: ResponseMocker,
):
    repository = HacsRepository(hacs=hacs)
    repository.data.full_name = "hacs-test-org/integration-basic"

    hacs.session = await client_session_proxy(hacs.hass)
    manifest = await repository.get_hacs_json(version=version)

    if name:
        assert manifest.name == name
    else:
        assert manifest is None
