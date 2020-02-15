"""Task Factory Test Suite."""
# pylint: disable=missing-docstring
import asyncio
import pytest
from custom_components.hacs.hacsbase.task_factory import HacsTaskFactory


@pytest.mark.asyncio
async def test_runtime_error():  # Issue#927
    factory = HacsTaskFactory()
    factory.tasks.append(asyncio.sleep(0.1))
    factory.tasks.append(factory.execute())

    await factory.execute()


@pytest.mark.asyncio
async def test_no_tasks():
    factory = HacsTaskFactory()
    await factory.execute()
