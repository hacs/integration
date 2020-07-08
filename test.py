import asyncio
from custom_components.hacs.helpers.functions.check import async_run_repository_checks
from tests.dummy_repository import dummy_repository_integration


async def test():
    """Example usage of pyhaversion."""
    await async_run_repository_checks(dummy_repository_integration())


loop = asyncio.get_event_loop()
loop.run_until_complete(test())
