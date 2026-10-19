import pytest

from custom_components.hacs.validate.integration_categories import Validator


@pytest.mark.parametrize(
    ("manifest", "failed"),
    [
        ({}, False),
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
    repository_integration.integration_manifest = manifest

    check = Validator(repository_integration)
    await check.execute_validation()
    assert check.failed is failed
