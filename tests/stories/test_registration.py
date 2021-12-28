"""Test repository registration."""
import base64
import json

from aresponses import ResponsesMockServer
import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.enums import HacsCategory

from tests.sample_data import (
    category_test_treefiles,
    integration_manifest,
    release_data,
    repository_data,
    response_rate_limit_header,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "category",
    (
        HacsCategory.INTEGRATION,
        HacsCategory.NETDAEMON,
        HacsCategory.PLUGIN,
        HacsCategory.PYTHON_SCRIPT,
        HacsCategory.THEME,
    ),
)
async def test_registration(
    hacs: HacsBase,
    category: HacsCategory,
    aresponses: ResponsesMockServer,
) -> None:
    """Test repository registration."""
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(body=b"{}", headers=response_rate_limit_header, status=200),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test",
        "get",
        aresponses.Response(body=json.dumps(repository_data), headers=response_rate_limit_header),
    )

    aresponses.add(
        "api.github.com",
        "/repos/test/test/releases",
        "get",
        aresponses.Response(body=json.dumps(release_data), headers=response_rate_limit_header),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test/git/trees/3",
        "get",
        aresponses.Response(
            body=json.dumps(category_test_treefiles(category)),
            headers=response_rate_limit_header,
        ),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test/contents/custom_components/test/manifest.json",
        "get",
        aresponses.Response(
            body=json.dumps(
                {
                    "content": base64.b64encode(
                        json.dumps(integration_manifest).encode("utf-8")
                    ).decode("utf-8")
                }
            ),
            headers=response_rate_limit_header,
        ),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test/contents/hacs.json",
        "get",
        aresponses.Response(body=json.dumps({"name": "test"}), headers=response_rate_limit_header),
    )

    assert hacs.repositories.get_by_full_name("test/test") is None

    await hacs.async_register_repository("test/test", category, check=True)

    assert hacs.repositories.get_by_full_name("test/test") is not None
