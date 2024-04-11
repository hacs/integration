from custom_components.hacs.validate.description import Validator


async def test_repository_no_description(repository):
    repository.data.description = ""
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


async def test_repository_hacs_description(repository):
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed
