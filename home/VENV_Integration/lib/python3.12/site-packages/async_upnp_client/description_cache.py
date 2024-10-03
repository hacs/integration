# -*- coding: utf-8 -*-
"""async_upnp_client.description_cache module."""

import asyncio
import logging
from typing import Any, Dict, Mapping, Optional, Tuple, Union, cast

import aiohttp
import defusedxml.ElementTree as DET

from async_upnp_client.client import UpnpRequester
from async_upnp_client.const import HttpRequest
from async_upnp_client.exceptions import UpnpResponseError
from async_upnp_client.utils import etree_to_dict

_LOGGER = logging.getLogger(__name__)


_UNDEF = object()


DescriptionType = Optional[Mapping[str, Any]]


def _description_xml_to_dict(description_xml: str) -> Optional[Mapping[str, str]]:
    """Convert description (XML) to dict."""
    try:
        tree = DET.fromstring(description_xml)
    except DET.ParseError as err:
        _LOGGER.debug("Error parsing %s: %s", description_xml, err)
        return None

    root = etree_to_dict(tree).get("root")
    if root is None:
        return None

    return root.get("device")


class DescriptionCache:
    """Cache for descriptions (xml)."""

    def __init__(self, requester: UpnpRequester):
        """Initialize."""
        self._requester = requester
        self._cache_dict: Dict[str, Union[asyncio.Event, DescriptionType]] = {}

    async def async_get_description_xml(self, location: str) -> Optional[str]:
        """Get a description as XML, either from cache or download it."""
        try:
            return await self._async_fetch_description(location)
        except Exception:  # pylint: disable=broad-except
            # If it fails, cache the failure so we do not keep trying over and over
            _LOGGER.exception("Failed to fetch description from: %s", location)

        return None

    def peek_description_dict(
        self, location: Optional[str]
    ) -> Tuple[bool, DescriptionType]:
        """Peek a description as dict, only try the cache."""
        if location is None:
            return True, None

        description = self._cache_dict.get(location, _UNDEF)
        if description is _UNDEF:
            return False, None

        if isinstance(description, asyncio.Event):
            return False, None

        return True, cast(DescriptionType, description)

    async def async_get_description_dict(
        self, location: Optional[str]
    ) -> DescriptionType:
        """Get a description as dict, either from cache or download it."""
        if location is None:
            return None

        cache_dict_or_evt = self._cache_dict.get(location, _UNDEF)
        if isinstance(cache_dict_or_evt, asyncio.Event):
            await cache_dict_or_evt.wait()
        elif cache_dict_or_evt is _UNDEF:
            evt = self._cache_dict[location] = asyncio.Event()
            try:
                description_xml = await self.async_get_description_xml(location)
            except UpnpResponseError:
                self._cache_dict[location] = None
            else:
                if description_xml:
                    self._cache_dict[location] = _description_xml_to_dict(
                        description_xml
                    )
                else:
                    self._cache_dict[location] = None
            evt.set()

        return cast(DescriptionType, self._cache_dict[location])

    def uncache_description(self, location: str) -> None:
        """Uncache a description."""
        if location in self._cache_dict:
            del self._cache_dict[location]

    async def _async_fetch_description(self, location: str) -> Optional[str]:
        """Download a description from location."""
        try:
            for _ in range(2):
                request = HttpRequest("GET", location, {}, None)
                response = await self._requester.async_http_request(request)
                if response.status_code != 200:
                    raise UpnpResponseError(
                        status=response.status_code, headers=response.headers
                    )

                return response.body
                # Samsung Smart TV sometimes returns an empty document the
                # first time. Retry once.
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.debug("Error fetching %s: %s", location, err)

        return None
