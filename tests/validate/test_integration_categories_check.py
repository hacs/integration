import logging
from unittest.mock import AsyncMock

from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent
import pytest

from custom_components.hacs.validate.integration_categories import Validator


def _set_manifest_tree(repository):
    repository.tree = [
        AIOGitHubAPIRepositoryTreeContent(
            {"path": "manifest.json", "type": "file"}, "test/test", "main",
        ),
    ]


async def test_integration_categories_no_manifest(repository_integration):
    repository_integration.integration_manifest = {}
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
    _set_manifest_tree(repository_integration)
    repository_integration.integration_manifest = manifest
    repository_integration.get_integration_manifest = AsyncMock()

    check = Validator(repository_integration)
    await check.execute_validation()
    assert check.failed is failed
    repository_integration.get_integration_manifest.assert_not_called()


async def test_integration_categories_fetches_manifest_when_not_loaded(repository_integration):
    _set_manifest_tree(repository_integration)
    repository_integration.integration_manifest = {}
    repository_integration.get_integration_manifest = AsyncMock(
        return_value={"categories": ["unknown"]}
    )

    check = Validator(repository_integration)
    await check.execute_validation()
    assert check.failed
    repository_integration.get_integration_manifest.assert_awaited_once_with(
        version=repository_integration.ref
    )


async def test_integration_categories_missing_is_a_warning(
    repository_integration, caplog: pytest.LogCaptureFixture
):
    _set_manifest_tree(repository_integration)
    repository_integration.integration_manifest = {"domain": "test"}

    check = Validator(repository_integration)
    await check.execute_validation()
    assert not check.failed
    assert any(
        record.levelno == logging.WARNING and "has no categories" in record.getMessage()
        for record in caplog.records
    )
