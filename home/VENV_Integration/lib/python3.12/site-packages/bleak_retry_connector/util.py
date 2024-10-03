from __future__ import annotations

import sys

if sys.version_info[:2] < (3, 11):
    from async_timeout import (  # noqa: F401 # pragma: no cover
        timeout as asyncio_timeout,
    )
else:
    from asyncio import timeout as asyncio_timeout  # noqa: F401 # pragma: no cover
