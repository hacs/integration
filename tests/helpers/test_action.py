"""Test action."""
# pylint: disable=missing-docstring,invalid-name

# pylint: disable=missing-docstring
import pytest

from tests.dummy_repository import dummy_repository_integration


@pytest.mark.asyncio
async def test_integration_brands():
    repository = dummy_repository_integration()
