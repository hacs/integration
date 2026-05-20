from unittest.mock import MagicMock

import pytest

from custom_components.hacs.validate.license import OPEN_SOURCE_LICENSES, Validator


async def test_repository_no_license(repository):
    repository.repository_object = MagicMock()
    repository.repository_object.attributes = {"license": None}
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


async def test_repository_unrecognized_license(repository):
    repository.repository_object = MagicMock()
    repository.repository_object.attributes = {
        "license": {"key": "other", "name": "Other", "spdx_id": "NOASSERTION"},
    }
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


async def test_repository_non_oss_license(repository):
    repository.repository_object = MagicMock()
    repository.repository_object.attributes = {
        "license": {"key": "cc-by-nc-4.0", "name": "Creative Commons Attribution Non Commercial 4.0", "spdx_id": "CC-BY-NC-4.0"},
    }
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


@pytest.mark.parametrize("license_key", OPEN_SOURCE_LICENSES)
async def test_repository_valid_license(repository, license_key):
    repository.repository_object = MagicMock()
    repository.repository_object.attributes = {
        "license": {"key": license_key, "name": f"License {license_key}", "spdx_id": license_key.upper()},
    }
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed
