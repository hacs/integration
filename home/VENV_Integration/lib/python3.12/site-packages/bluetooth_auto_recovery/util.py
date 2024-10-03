from __future__ import annotations

import sys

if sys.version_info[:2] < (3, 11):
    from async_timeout import timeout as asyncio_timeout  # noqa: F401
else:
    from asyncio import timeout as asyncio_timeout  # noqa: F401
