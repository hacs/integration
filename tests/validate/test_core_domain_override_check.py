import json

from custom_components.hacs.validate.core_domain_override import (
    CORE_INTEGRATIONS_URL,
    Validator,
)

from tests.common import MockedResponse, ResponseMocker


async def test_domain_not_in_core(repository, response_mocker: ResponseMocker):
    response_mocker.add(
        CORE_INTEGRATIONS_URL,
        MockedResponse(content=json.dumps({"hue": {}})),
    )
    repository.data.domain = "test"
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


async def test_domain_overrides_core_domain(repository, response_mocker: ResponseMocker):
    response_mocker.add(
        CORE_INTEGRATIONS_URL,
        MockedResponse(content=json.dumps({"test": {}})),
    )
    repository.data.domain = "test"
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


async def test_core_integrations_fetch_failure(repository, response_mocker: ResponseMocker):
    response_mocker.add(CORE_INTEGRATIONS_URL, MockedResponse(status=500))
    repository.data.domain = "test"
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


async def test_core_integrations_invalid_json(repository, response_mocker: ResponseMocker):
    response_mocker.add(CORE_INTEGRATIONS_URL, MockedResponse(content="not json"))
    repository.data.domain = "test"
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


async def test_no_domain_skips_fetch(repository, response_mocker: ResponseMocker):
    # Without a domain there is nothing to compare, the missing manifest is
    # reported by the integration_manifest check instead.
    response_mocker.add(CORE_INTEGRATIONS_URL, MockedResponse(status=500))
    repository.data.domain = None
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed
