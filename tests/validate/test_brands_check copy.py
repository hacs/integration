import json

import pytest

from custom_components.hacs.validate.brands import Validator

from tests.sample_data import response_rate_limit_header


@pytest.mark.asyncio
async def test_added_to_brands(repository, aresponses):
    aresponses.add(
        "brands.home-assistant.io",
        "/domains.json",
        "get",
        aresponses.Response(
            body=json.dumps({"custom": ["test"]}),
            headers=response_rate_limit_header,
        ),
    )
    repository.data.domain = "test"
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


@pytest.mark.asyncio
async def test_not_added_to_brands(repository, aresponses):
    aresponses.add(
        "brands.home-assistant.io",
        "/domains.json",
        "get",
        aresponses.Response(
            body=json.dumps({"custom": []}),
            headers=response_rate_limit_header,
        ),
    )
    repository.data.domain = "test"
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed
