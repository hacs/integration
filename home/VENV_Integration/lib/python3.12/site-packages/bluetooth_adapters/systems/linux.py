from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiooui
from uart_devices import BluetoothDevice as UARTBluetoothDevice
from uart_devices import NotAUARTDeviceError
from usb_devices import BluetoothDevice as USBBluetoothDevice
from usb_devices import NotAUSBDeviceError

from ..adapters import BluetoothAdapters
from ..const import EMPTY_MAC_ADDRESS, UNIX_DEFAULT_BLUETOOTH_ADAPTER
from ..dbus import BlueZDBusObjects
from ..history import AdvertisementHistory
from ..models import AdapterDetails
from .linux_hci import get_adapters_from_hci

_LOGGER = logging.getLogger(__name__)


class LinuxAdapters(BluetoothAdapters):
    """Class for getting the bluetooth adapters on a Linux system."""

    def __init__(self) -> None:
        """Initialize the adapter."""
        self._bluez = BlueZDBusObjects()
        self._adapters: dict[str, AdapterDetails] | None = None
        self._devices: dict[str, UARTBluetoothDevice | USBBluetoothDevice] = {}
        self._hci_output: dict[int, dict[str, Any]] | None = None

    async def refresh(self) -> None:
        """Refresh the adapters."""
        loop = asyncio.get_running_loop()
        load_task = asyncio.create_task(self._bluez.load())
        adapters_from_hci_future = loop.run_in_executor(None, get_adapters_from_hci)
        futures: list[asyncio.Future[Any]] = [load_task, adapters_from_hci_future]
        if not aiooui.is_loaded():
            futures.append(aiooui.async_load())
        await asyncio.gather(*futures)
        self._hci_output = await adapters_from_hci_future
        self._adapters = None  # clear cache
        self._devices = {}
        await loop.run_in_executor(None, self._refresh_devices)

    def _refresh_devices(self) -> None:
        """Refresh the devices."""
        for adapter in self._bluez.adapter_details:
            i = int(adapter[3:])
            for cls in (USBBluetoothDevice, UARTBluetoothDevice):
                dev = cls(i)
                self._devices[adapter] = dev
                try:
                    dev.setup()
                except (NotAUARTDeviceError, NotAUSBDeviceError):
                    continue
                except FileNotFoundError:
                    break
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected error setting up device hci%s", dev)
                    break
                else:
                    break

    @property
    def history(self) -> dict[str, AdvertisementHistory]:
        """Get the bluez history."""
        return self._bluez.history

    @property
    def adapters(self) -> dict[str, AdapterDetails]:
        """Get the adapter details."""
        manufacturer: str | None
        if self._adapters is None:
            adapters: dict[str, AdapterDetails] = {}
            if self._hci_output:
                for hci_details in self._hci_output.values():
                    name = hci_details["name"]
                    mac_address = hci_details["bdaddr"].upper()
                    if mac_address == EMPTY_MAC_ADDRESS:
                        manufacturer = None
                    else:
                        manufacturer = aiooui.get_vendor(mac_address)
                    adapters[name] = AdapterDetails(
                        address=mac_address,
                        sw_version="Unknown",
                        hw_version=None,
                        passive_scan=False,  # assume false if we don't know
                        manufacturer=manufacturer,
                        product=None,
                        vendor_id=None,
                        product_id=None,
                    )
            adapter_details = self._bluez.adapter_details
            for adapter, details in adapter_details.items():
                if not (adapter1 := details.get("org.bluez.Adapter1")):
                    continue
                mac_address = adapter1["Address"]
                device = self._devices[adapter]
                product: str | None = None
                manufacturer = None
                vendor_id: str | None = None
                product_id: str | None = None
                if isinstance(device, USBBluetoothDevice):
                    usb_device = device.usb_device
                    if mac_address != EMPTY_MAC_ADDRESS and (
                        usb_device is None
                        or usb_device.vendor_id == usb_device.manufacturer
                        or usb_device.manufacturer is None
                        or usb_device.manufacturer == "Unknown"
                    ):
                        manufacturer = aiooui.get_vendor(mac_address)
                    elif usb_device is not None:
                        manufacturer = usb_device.manufacturer
                    if usb_device is not None:
                        product = usb_device.product
                        vendor_id = usb_device.vendor_id
                        product_id = usb_device.product_id
                elif isinstance(device, UARTBluetoothDevice):
                    uart_device = device.uart_device
                    if uart_device is None:
                        if mac_address != EMPTY_MAC_ADDRESS:
                            manufacturer = aiooui.get_vendor(mac_address)
                    else:
                        product = uart_device.product

                        if mac_address == EMPTY_MAC_ADDRESS:
                            manufacturer = uart_device.manufacturer
                        else:
                            manufacturer = (
                                aiooui.get_vendor(mac_address)
                                or uart_device.manufacturer
                            )

                adapters[adapter] = AdapterDetails(
                    address=mac_address,
                    sw_version=adapter1["Name"],  # This is actually the BlueZ version
                    hw_version=adapter1.get("Modalias"),
                    passive_scan="org.bluez.AdvertisementMonitorManager1" in details,
                    manufacturer=manufacturer,
                    product=product,
                    vendor_id=vendor_id,
                    product_id=product_id,
                )
            self._adapters = adapters
        return self._adapters

    @property
    def default_adapter(self) -> str:
        """Get the default adapter."""
        return UNIX_DEFAULT_BLUETOOTH_ADAPTER
