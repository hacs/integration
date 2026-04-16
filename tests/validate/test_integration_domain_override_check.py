from custom_components.hacs.validate.integration_domain_override import Validator

from tests.common import MockedResponse, ResponseMocker


async def test_domain_is_not_core(repository, response_mocker: ResponseMocker):
    response_mocker.add(
        "https://rc.home-assistant.io/integrations.json",
        MockedResponse(content={"hue": {}, "mqtt": {}}),
    )
    repository.data.domain = "my_custom_domain"
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed


async def test_domain_is_core(repository, response_mocker: ResponseMocker):
    response_mocker.add(
        "https://rc.home-assistant.io/integrations.json",
        MockedResponse(content={"hue": {}, "mqtt": {}}),
    )
    repository.data.domain = "hue"
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


async def test_empty_integrations_list(repository, response_mocker: ResponseMocker):
    response_mocker.add(
        "https://rc.home-assistant.io/integrations.json",
        MockedResponse(content={}),
    )
    repository.data.domain = "my_custom_domain"
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed
