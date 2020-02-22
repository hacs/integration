import asyncio
import aiohttp

from pyhaversion import PyPiVersion


async def test():
    """Example usage of pyhaversion."""
    async with aiohttp.ClientSession() as session:
        data = PyPiVersion(loop, session=session)
        await data.get_version()
        print(data.version.split(".")[1])


loop = asyncio.get_event_loop()
loop.run_until_complete(test())
