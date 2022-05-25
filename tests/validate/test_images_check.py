import pytest

from custom_components.hacs.validate.images import Validator


@pytest.mark.asyncio
async def test_repository_has_images(repository):
    repository.data.has_issues = True
    check = Validator(repository)

    async def _async_get_info_file_contents(*_, **__):
        return """
![-shielded
![valid]
"""

    repository.async_get_info_file_contents = _async_get_info_file_contents
    await check.execute_validation()
    assert not check.failed


@pytest.mark.asyncio
async def test_repository_has_not_images(repository):
    repository.data.has_issues = False
    check = Validator(repository)

    async def _async_get_info_file_contents(*_, **__):
        return """
![-shielded
"""

    repository.async_get_info_file_contents = _async_get_info_file_contents

    await check.execute_validation()
    assert check.failed
