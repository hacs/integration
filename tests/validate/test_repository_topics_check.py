from custom_components.hacs.validate.topics import Validator


async def test_repository_no_topics(repository):
    repository.data.topics = []
    check = Validator(repository)
    await check.execute_validation()
    assert check.failed


async def test_repository_hacs_topics(repository):
    repository.data.topics = ["test"]
    check = Validator(repository)
    await check.execute_validation()
    assert not check.failed
