"""Test fs_util."""


import pytest

from custom_components.hacs.utils.file_system import (
    async_exists,
    async_remove,
    async_remove_directory,
)


async def test_async_exists(hass, tmpdir):
    """Test async_exists."""
    assert not await async_exists(hass, tmpdir / "tmptmp")

    open(tmpdir / "tmptmp", "w").close()
    assert await async_exists(hass, tmpdir / "tmptmp")


async def test_async_remove(hass, tmpdir):
    """Test async_remove."""
    assert not await async_exists(hass, tmpdir / "tmptmp")
    with pytest.raises(FileNotFoundError):
        await async_remove(hass, tmpdir / "tmptmp")
    with pytest.raises(FileNotFoundError):
        await async_remove(hass, tmpdir / "tmptmp", missing_ok=False)
    await async_remove(hass, tmpdir / "tmptmp", missing_ok=True)

    open(tmpdir / "tmptmp", "w").close()
    await async_remove(hass, tmpdir / "tmptmp")
    assert not await async_exists(hass, tmpdir / "tmptmp")

    open(tmpdir / "tmptmp", "w").close()
    await async_remove(hass, tmpdir / "tmptmp", missing_ok=False)
    assert not await async_exists(hass, tmpdir / "tmptmp")

    open(tmpdir / "tmptmp", "w").close()
    await async_remove(hass, tmpdir / "tmptmp", missing_ok=True)
    assert not await async_exists(hass, tmpdir / "tmptmp")


async def test_async_remove_directory(hass, tmpdir):
    """Test async_remove_directory."""
    assert not await async_exists(hass, tmpdir / "tmptmp")
    with pytest.raises(FileNotFoundError):
        await async_remove_directory(hass, tmpdir / "tmptmp")
    with pytest.raises(FileNotFoundError):
        await async_remove_directory(hass, tmpdir / "tmptmp", missing_ok=False)

    assert not await async_exists(hass, tmpdir / "tmptmp")
    await async_remove_directory(hass, tmpdir / "tmptmp", missing_ok=True)

    (tmpdir / "tmptmp").mkdir()
    assert await async_exists(hass, tmpdir / "tmptmp")
    await async_remove_directory(hass, tmpdir / "tmptmp")
    assert not await async_exists(hass, tmpdir / "tmptmp")

    (tmpdir / "tmptmp").mkdir()
    assert await async_exists(hass, tmpdir / "tmptmp")
    await async_remove_directory(hass, tmpdir / "tmptmp", missing_ok=False)
    assert not await async_exists(hass, tmpdir / "tmptmp")

    (tmpdir / "tmptmp").mkdir()
    assert await async_exists(hass, tmpdir / "tmptmp")
    await async_remove_directory(hass, tmpdir / "tmptmp", missing_ok=True)
    assert not await async_exists(hass, tmpdir / "tmptmp")
