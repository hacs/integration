from typing import Any

import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.repositories.base import HacsRepository

from tests.common import MockedResponse, ResponseMocker, client_session_proxy


@pytest.mark.parametrize(
    "data,result",
    [
        ({"installed": True, "installed_version": "1.0.0"}, "Example readme file (1.0.0)"),
        (
            {"installed": True, "installed_version": "1.0.0", "last_version": "2.0.0"},
            "Example readme file (1.0.0)",
        ),
        ({"installed": False, "last_version": "2.0.0"}, "Example readme file (2.0.0)"),
        ({"installed": False, "last_version": "99.99.99"}, None),
    ],
)
@pytest.mark.asyncio
async def test_validate_repository(
    hacs: HacsBase,
    data: dict[str, Any],
    result: str | None,
    response_mocker: ResponseMocker,
):
    repository = HacsRepository(hacs=hacs)
    repository.data.full_name = "hacs-test-org/integration-basic"
    for key, value in data.items():
        setattr(repository.data, key, value)

    if result is None:
        response_mocker.add(
            f"https://raw.githubusercontent.com/hacs-test-org/integration-basic/{data['last_version']}/README.md",
            MockedResponse(status=404),
        )

    hacs.session = await client_session_proxy(hacs.hass)
    docs = await repository.get_documentation(filename="README.md")

    if result:
        assert result in docs
    else:
        assert result is None
