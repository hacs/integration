from typing import Any

import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.repositories.base import HacsRepository

from tests.common import ResponseMocker, client_session_proxy


@pytest.mark.parametrize(
    ("data", "integration", "expected_result"),
    [
        ({"installed": True, "installed_version": "1.0.0"}, "integration-basic", "## Example readme file (1.0.0)"),
        (
            {"installed": True, "installed_version": "1.0.0", "last_version": "2.0.0"}, "integration-basic",
            "## Example readme file (1.0.0)",
        ),
        ({"installed": False, "last_version": "2.0.0"}, "integration-basic", "## Example readme file (2.0.0)"),
        ({"installed": False, "last_version": "99.99.99"}, "integration-basic", None),
        ({"installed": False, "last_version": "1.0.0"}, "integration-basic-svg", "Example readme file <disabled>data</disabled>(1.0.0)"),
    ],
)
async def test_get_documentation(
    hacs: HacsBase,
    data: dict[str, Any],
    integration: str,
    expected_result: str | None,
    response_mocker: ResponseMocker,
):
    repository = HacsRepository(hacs=hacs)
    repository.data.full_name = f"hacs-test-org/{integration}"
    for key, value in data.items():
        setattr(repository.data, key, value)

    hacs.session = await client_session_proxy(hacs.hass)
    docs = await repository.get_documentation(filename="README.md", version=None)

    assert docs == expected_result
