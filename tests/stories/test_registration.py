"""Test repository registration."""
import base64
import json

from aresponses import ResponsesMockServer
import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.enums import HacsCategory
from custom_components.hacs.exceptions import (
    AddonRepositoryException,
    HacsException,
    HomeAssistantCoreRepositoryException,
)

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

    content = base64.b64encode(json.dumps(integration_manifest).encode("utf-8"))
    aresponses.add(
        "api.github.com",
        "/repos/test/test/contents/custom_components/test/manifest.json",
        "get",
        aresponses.Response(
            body=json.dumps({"content": content.decode("utf-8")}),
            headers=response_rate_limit_header,
        ),
    )

    assert hacs.repositories.get_by_full_name("test/test") is None

    await hacs.async_register_repository("test/test", category, check=True)

    repository = hacs.repositories.get_by_full_name("test/test")

    assert repository is not None
    assert repository.data.category == category
    assert repository.data.full_name == "test/test"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "repository_full_name,expected_message",
    (
        ("home-assistant/core", HomeAssistantCoreRepositoryException.exception_message),
        ("home-assistant/addons", AddonRepositoryException.exception_message),
        ("hassio-addons/some-addon", AddonRepositoryException.exception_message),
        ("some-user/addons", AddonRepositoryException.exception_message),
        (
            "some-user/some-invalid-repo",
            "<Integration some-user/some-invalid-repo> Repository structure for main is not compliant",
        ),
    ),
)
async def test_registration_issues(
    hacs: HacsBase,
    repository_full_name: str,
    expected_message: str,
    aresponses: ResponsesMockServer,
) -> None:
    """Test repository registration."""
    repo_data = {**repository_data, "full_name": repository_full_name}
    aresponses.add(
        "api.github.com",
        f"/repos/{repository_full_name}",
        "get",
        aresponses.Response(body=json.dumps(repo_data), headers=response_rate_limit_header),
    )

    aresponses.add(
        "api.github.com",
        f"/repos/{repository_full_name}/releases",
        "get",
        aresponses.Response(body=json.dumps([]), headers=response_rate_limit_header),
    )

    aresponses.add(
        "api.github.com",
        f"/repos/{repository_full_name}/git/trees/main",
        "get",
        aresponses.Response(
            body=json.dumps(
                {
                    "tree": {
                        "home-assistant/core": [],
                        "home-assistant/addons": [
                            {"path": "repository.json", "type": "blob"},
                        ],
                        "hassio-addons/some-addon": [
                            {"path": "repository.json", "type": "blob"},
                        ],
                        "some-user/addons": [
                            {"path": "repository.yaml", "type": "blob"},
                        ],
                        "some-user/some-invalid-repo": [
                            {"path": "setup.py", "type": "blob"},
                        ],
                    }[repository_full_name]
                }
            ),
            headers=response_rate_limit_header,
        ),
    )

    assert hacs.repositories.get_by_full_name(repository_full_name) is None
    with pytest.raises(HacsException, match=expected_message):
        await hacs.async_register_repository(
            repository_full_name, HacsCategory.INTEGRATION, check=True
        )
