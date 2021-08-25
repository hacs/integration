import pytest

from custom_components.hacs.exceptions import HacsException


@pytest.mark.asyncio
async def test_installation_method(repository):
    with pytest.raises(HacsException):
        await repository.async_install()
    repository.content.path.local = ""

    with pytest.raises(HacsException):
        await repository.async_install()

    # repository.can_install = True

    await repository._async_post_install()
