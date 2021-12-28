"""Helpers: Information: get_repository."""
# pylint: disable=missing-docstring
import json

import pytest

from tests.sample_data import (
    repository_data,
    response_rate_limit_header,
    tree_files_base_integration,
)

TOKEN = "xxxxxxxxxxxxxxxxxxxxxxx"


@pytest.mark.asyncio
async def test_base(aresponses, repository_integration):
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(body=b"{}", headers=response_rate_limit_header),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test",
        "get",
        aresponses.Response(body=json.dumps(repository_data), headers=response_rate_limit_header),
    )
    aresponses.add(
        "api.github.com",
        "/rate_limit",
        "get",
        aresponses.Response(body=b"{}", headers=response_rate_limit_header),
    )
    aresponses.add(
        "api.github.com",
        "/repos/test/test/git/trees/main",
        "get",
        aresponses.Response(
            body=json.dumps(tree_files_base_integration()),
            headers=response_rate_limit_header,
        ),
    )

    (
        repository_integration.repository_object,
        _,
    ) = await repository_integration.async_get_legacy_repository_object()
    tree = await repository_integration.get_tree(
        repository_integration.repository_object.default_branch
    )
    filestocheck = [
        "custom_components/test/__init__.py",
        "custom_components/test/translations/en.json",
        "custom_components/test/manifest.json",
    ]
    for check in filestocheck:
        assert check in [x.full_path for x in tree]
