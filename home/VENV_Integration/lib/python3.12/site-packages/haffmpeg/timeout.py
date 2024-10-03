"""Timeouts."""
import sys

if sys.version_info[:2] < (3, 11):
    # pylint: disable-next=unused-import
    from async_timeout import timeout as asyncio_timeout  # noqa: F401
else:
    from asyncio import timeout as asyncio_timeout  # noqa: F401
