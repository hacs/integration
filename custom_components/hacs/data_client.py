"""HACS Data client."""
from __future__ import annotations

import asyncio
from typing import Any

from aiohttp import ClientSession, ClientTimeout

from .exceptions import HacsException, HacsNotModifiedException


class HacsDataClient:
    """HACS Data client."""

    def __init__(self, session: ClientSession, client_name: str) -> None:
        """Initialize."""
        self._client_name = client_name
        self._etags = {}
        self._session = session

    async def _do_request(
        self,
        filename: str,
        section: str | None = None,
    ) -> dict[str, dict[str, Any]] | list[str]:
        """Do request."""
        endpoint = "/".join([v for v in [section, filename] if v is not None])
        try:
            response = await self._session.get(
                f"https://data-v2.hacs.xyz/{endpoint}",
                timeout=ClientTimeout(total=60),
                headers={
                    "User-Agent": self._client_name,
                    "If-None-Match": self._etags.get(endpoint, ""),
                },
            )
            if response.status == 304:
                raise HacsNotModifiedException() from None
            response.raise_for_status()
        except HacsNotModifiedException:
            raise
        except asyncio.TimeoutError:
            raise HacsException("Timeout of 60s reached") from None
        except Exception as exception:
            raise HacsException(f"Error fetching data from HACS: {exception}") from exception

        self._etags[endpoint] = response.headers.get("etag")

        return await response.json()

    async def get_data(self, section: str | None) -> dict[str, dict[str, Any]]:
        """Get data."""
        return await self._do_request(filename="data.json", section=section)

    async def get_repositories(self, section: str) -> list[str]:
        """Get repositories."""
        return await self._do_request(filename="repositories.json", section=section)
