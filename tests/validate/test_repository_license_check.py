from unittest.mock import MagicMock

from custom_components.hacs.validate.license import Validator


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


async def test_repository_valid_license(repository):
    repository.repository_object = MagicMock()
    repository.repository_object.attributes = {
        "license": {"key": "mit", "name": "MIT License", "spdx_id": "MIT"},
    }
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed
