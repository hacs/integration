from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent
import pytest

from custom_components.hacs.validate.integration_categories import Validator


async def test_integration_categories_no_manifest(repository_integration):
    check = Validator(repository_integration)
    await check.execute_validation()
    assert not check.failed


@pytest.mark.parametrize(
    ("manifest", "failed"),
    [
        ({"domain": "test"}, False),
        ({"categories": ["energy", "energy.ev_charging"]}, False),
        ({"categories": ["energy", "unknown"]}, True),
        ({"categories": ["energy", "energy"]}, True),
        ({"categories": ["energy", "climate", "lighting", "weather_alerts"]}, True),
        ({"categories": []}, True),
        ({"categories": "energy"}, True),
    ],
)
async def test_integration_categories(repository_integration, manifest: dict, failed: bool):
    repository_integration.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "manifest.json", "type": "file"}, "test/test", "main",
        ),
    ]

    async def _async_get_integration_manifest(**__):
        return manifest

    repository_integration.get_integration_manifest = _async_get_integration_manifest

    check = Validator(repository_integration)
    await check.execute_validation()
    assert check.failed is failed
