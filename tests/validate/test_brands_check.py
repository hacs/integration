import pytest

from custom_components.hacs.validate.brands import Validator

from tests.common import MockedResponse, ResponseMocker


@pytest.mark.asyncio
async def test_added_to_brands(repository, response_mocker: ResponseMocker):
    response_mocker.add(
        "https://brands.home-assistant.io/domains.json",
        MockedResponse(content={"custom": ["test"]}),
    )
    repository.data.domain = "test"
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


@pytest.mark.asyncio
async def test_not_added_to_brands(repository, response_mocker: ResponseMocker):
    response_mocker.add(
        "https://brands.home-assistant.io/domains.json", MockedResponse(content={"custom": []})
    )
    repository.data.domain = "test"
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed
