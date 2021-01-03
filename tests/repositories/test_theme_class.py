import pytest

from custom_components.hacs.helpers.classes.exceptions import HacsException


@pytest.mark.asyncio
async def test_async_post_installation(repository_theme):
    await repository_theme.async_post_installation()


@pytest.mark.asyncio
async def test_async_post_registration(repository_theme):
    await repository_theme.async_post_registration()


@pytest.mark.asyncio
async def test_validate_repository(repository_theme):
    with pytest.raises(HacsException):
        await repository_theme.validate_repository()


@pytest.mark.asyncio
async def test_update_repository(repository_theme):
    await repository_theme.update_repository()
