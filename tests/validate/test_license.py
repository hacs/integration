import json
from unittest.mock import MagicMock

import pytest

from custom_components.hacs.validate.license import SPDX_LICENSE_LIST_URL, Validator

from tests.common import MockedResponse, ResponseMocker


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


async def test_repository_missing_spdx_id(repository):
    repository.repository_object = MagicMock()
    repository.repository_object.attributes = {
        "license": {"key": "other", "name": "Other"},
    }
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


async def test_repository_non_osi_license(repository):
    repository.repository_object = MagicMock()
    repository.repository_object.attributes = {
        "license": {
            "key": "cc0-1.0",
            "name": "Creative Commons Zero v1.0 Universal",
            "spdx_id": "CC0-1.0",
        },
    }
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


async def test_spdx_license_list_fetch_failure(repository, response_mocker: ResponseMocker):
    response_mocker.add(SPDX_LICENSE_LIST_URL, MockedResponse(status=500))
    repository.repository_object = MagicMock()
    repository.repository_object.attributes = {
        # An uncommon (non-cached) license so the check falls back to the fetch.
        "license": {"key": "isc", "name": "ISC License", "spdx_id": "ISC"},
    }
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


@pytest.mark.parametrize("spdx_id", ["MIT", "Apache-2.0", "GPL-3.0"])
async def test_repository_popular_license_skips_fetch(
    repository, response_mocker: ResponseMocker, spdx_id
):
    # A popular license is cached and must pass without depending on the SPDX
    # list fetch, so even a broken fetch (500) must not affect the result.
    response_mocker.add(SPDX_LICENSE_LIST_URL, MockedResponse(status=500))
    repository.repository_object = MagicMock()
    repository.repository_object.attributes = {
        "license": {
            "key": spdx_id.lower(),
            "name": f"License {spdx_id}",
            "spdx_id": spdx_id,
        },
    }
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


async def test_repository_uncommon_osi_license(repository, response_mocker: ResponseMocker):
    # An uncommon OSI-approved license is not cached, so it falls back to the
    # fetched SPDX list to be validated.
    response_mocker.add(
        SPDX_LICENSE_LIST_URL,
        MockedResponse(
            content=json.dumps({"licenses": [{"licenseId": "ISC", "isOsiApproved": True}]})
        ),
    )
    repository.repository_object = MagicMock()
    repository.repository_object.attributes = {
        "license": {"key": "isc", "name": "ISC License", "spdx_id": "ISC"},
    }
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed
