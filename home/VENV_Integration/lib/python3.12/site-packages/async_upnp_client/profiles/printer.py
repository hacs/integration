# -*- coding: utf-8 -*-
"""async_upnp_client.profiles.printer module."""

import logging
from typing import List, NamedTuple, Optional

from async_upnp_client.profiles.profile import UpnpProfileDevice

_LOGGER = logging.getLogger(__name__)


PrinterAttributes = NamedTuple(
    "PrinterAttributes",
    [
        ("printer_state", str),
        ("printer_state_reasons", str),
        ("job_id_list", List[int]),
        ("job_id", int),
    ],
)


class PrinterDevice(UpnpProfileDevice):
    """Representation of a printer device."""

    DEVICE_TYPES = [
        "urn:schemas-upnp-org:device:printer:1",
    ]

    _SERVICE_TYPES = {
        "BASIC": {
            "urn:schemas-upnp-org:service:PrintBasic:1",
        },
    }

    async def async_get_printer_attributes(self) -> Optional[PrinterAttributes]:
        """Get printer attributes."""
        action = self._action("BASIC", "GetPrinterAttributes")
        if not action:
            return None

        result = await action.async_call()
        return PrinterAttributes(
            result["PrinterState"],
            result["PrinterStateReasons"],
            [int(x) for x in result["JobIdList"].split(",")],
            int(result["JobId"]),
        )
