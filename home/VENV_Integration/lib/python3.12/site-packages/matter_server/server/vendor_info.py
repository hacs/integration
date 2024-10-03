"""Fetches vendor info from the CSA."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiohttp import ClientError, ClientSession

from ..common.helpers.api import api_command
from ..common.helpers.util import dataclass_from_dict, dataclass_to_dict
from ..common.models import APICommand, VendorInfo as VendorInfoModel

if TYPE_CHECKING:
    from .server import MatterServer

LOGGER = logging.getLogger(__name__)
PRODUCTION_URL = "https://on.dcl.csa-iot.org"
DATA_KEY_VENDOR_INFO = "vendor_info"


TEST_VENDOR = VendorInfoModel(
    vendor_id=65521,
    vendor_name="Test",
    company_legal_name="Test",
    company_preferred_name="Test",
    vendor_landing_page_url="https://csa-iot.org",
    creator="",
)
NABUCASA_VENDOR = VendorInfoModel(
    vendor_id=4939,
    vendor_name="Nabu Casa",
    company_legal_name="Nabu Casa Inc.",
    company_preferred_name="Nabu Casa",
    vendor_landing_page_url="https://nabucasa.com/",
    creator="",
)


class VendorInfo:
    """Fetches vendor info from the CSA and handles api calls to get it."""

    def __init__(self, server: MatterServer):
        """Initialize the vendor info."""
        self._data: dict[int, VendorInfoModel] = {
            # add test vendor ID
            TEST_VENDOR.vendor_id: TEST_VENDOR,
            # add nabucasa vendor while we're not yet certified
            NABUCASA_VENDOR.vendor_id: NABUCASA_VENDOR,
        }
        self._server = server

    async def start(self) -> None:
        """Async initialize the vendor info."""
        self._load_vendors()
        await self._fetch_vendors()
        self._save_vendors()

    def _load_vendors(self) -> None:
        """Load vendor info from storage."""
        LOGGER.info("Loading vendor info from storage.")
        vendor_count = 0
        data = self._server.storage.get(DATA_KEY_VENDOR_INFO, {})
        for vendor_id, vendor_info in data.items():
            self._data[vendor_id] = dataclass_from_dict(VendorInfoModel, vendor_info)
            vendor_count += 1
        LOGGER.info("Loaded %s vendors from storage.", vendor_count)

    async def _fetch_vendors(self) -> None:
        """Fetch the vendor names from the CSA."""
        LOGGER.info("Fetching the latest vendor info from DCL.")
        vendors: dict[int, VendorInfoModel] = {}
        try:
            async with ClientSession(raise_for_status=True) as session:
                page_token: str | None = ""
                while page_token is not None:
                    async with session.get(
                        f"{PRODUCTION_URL}/dcl/vendorinfo/vendors",
                        params={"pagination.key": page_token},
                    ) as response:
                        data = await response.json()
                        for vendorinfo in data["vendorInfo"]:
                            vendors[vendorinfo["vendorID"]] = VendorInfoModel(
                                vendor_id=vendorinfo["vendorID"],
                                vendor_name=vendorinfo["vendorName"],
                                company_legal_name=vendorinfo["companyLegalName"],
                                company_preferred_name=vendorinfo[
                                    "companyPreferredName"
                                ],
                                vendor_landing_page_url=vendorinfo[
                                    "vendorLandingPageURL"
                                ],
                                creator=vendorinfo["creator"],
                            )
                    page_token = data.get("pagination", {}).get("next_key", None)
        except ClientError as err:
            LOGGER.error("Unable to fetch vendor info from DCL: %s", err)
        else:
            LOGGER.info("Fetched %s vendors from DCL.", len(vendors))

        self._data.update(vendors)

    def _save_vendors(self) -> None:
        """Save vendor info to storage."""
        LOGGER.info("Saving vendor info to storage.")
        self._server.storage.set(
            DATA_KEY_VENDOR_INFO,
            {
                vendor_id: dataclass_to_dict(vendor_info)
                for vendor_id, vendor_info in self._data.items()
            },
        )

    @api_command(APICommand.GET_VENDOR_NAMES)
    async def get_vendor_names(
        self, filter_vendors: list[int] | None = None
    ) -> dict[int, str]:
        """Get a map of vendor ids to vendor names."""
        if filter_vendors:
            vendors: dict[int, str] = {}
            for vendor_id in filter_vendors:
                if vendor_id in filter_vendors and vendor_id in self._data:
                    vendors[vendor_id] = self._data[vendor_id].vendor_name
            return vendors

        return {
            vendor_id: vendor_info.vendor_name
            for vendor_id, vendor_info in self._data.items()
        }
