from unittest.mock import patch

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


async def test_get_hacs_json_with_exception(hacs: HacsBase):
    """Test that get_hacs_json returns None on exception due to decorator."""
    repository = HacsRepository(hacs=hacs)
    repository.data.full_name = "hacs-test-org/integration-basic"

    # Mock get_hacs_json_raw to raise an exception
    with patch.object(repository, "get_hacs_json_raw", side_effect=Exception("Test exception")):
        result = await repository.get_hacs_json(version="1.0.0")
        assert result is None

    # Mock HacsManifest.from_dict to raise an exception
    with patch("custom_components.hacs.repositories.base.HacsManifest.from_dict", side_effect=ValueError("Invalid manifest")):
        result = await repository.get_hacs_json(version="1.0.0")
        assert result is None
