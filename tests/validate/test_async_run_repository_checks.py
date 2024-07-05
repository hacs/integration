from unittest.mock import patch

import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.repositories.integration import HacsIntegrationRepository
from custom_components.hacs.validate.manager import ValidationManager


async def test_async_run_repository_checks(
    hacs: HacsBase,
    repository_integration: HacsIntegrationRepository,
):
    hacs.validation = ValidationManager(hacs=hacs, hass=hacs.hass)
    hacs.system.action = False

    await hacs.validation.async_run_repository_checks(repository_integration)

    hacs.system.action = True
    repository_integration.tree = []
    with pytest.raises(SystemExit):
        await hacs.validation.async_run_repository_checks(repository_integration)

    with patch(
        "custom_components.hacs.validate.manager.ValidationManager.validators", return_value=[],
    ):
        await hacs.validation.async_run_repository_checks(repository_integration)
