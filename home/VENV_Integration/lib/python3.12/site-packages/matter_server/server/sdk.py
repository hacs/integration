"""Module to wrap Python CHIP SDK classes.

This module contains wrapper for the official Matter/CHIP SDK classes. The goal is to
make the classes easier to use in asyncio environment and our use case in general. It
also makes the API more pythonic where possible.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache, partial
import logging
import time
from typing import TYPE_CHECKING, Any, TypeVar, cast

from chip.clusters import Attribute, Objects as Clusters
from chip.clusters.Attribute import AttributeWriteResult
from chip.discovery import FilterType
from chip.exceptions import ChipStackError

from ..common.errors import (
    NodeNotResolving,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path

    from chip.ChipDeviceCtrl import (
        ChipDeviceController,
        CommissioningParameters,
        DeviceProxyWrapper,
    )
    from chip.discovery import DiscoveryType
    from chip.native import PyChipError

    from .server import MatterServer

_T = TypeVar("_T")

LOGGER = logging.getLogger(__name__)

# pylint: disable=too-many-public-methods


class ChipDeviceControllerWrapper:
    """Class exposing CHIP/Matter devices controller features.

    This class is responsible for managing the Matter devices. It should be seen mostly
    as a wrapper of the ChipDeviceController class provided by the Matter/CHIP SDK.
    """

    compressed_fabric_id: int
    fabric_id_hex: str
    _chip_controller: ChipDeviceController

    def __init__(self, server: MatterServer, paa_root_cert_dir: Path):
        """Initialize the device controller."""
        self.server = server

        self._node_lock: dict[int, asyncio.Lock] = {}
        self._subscriptions: dict[int, Attribute.SubscriptionTransaction] = {}

        # Instantiate the underlying ChipDeviceController instance on the Fabric
        self._chip_controller = self.server.stack.fabric_admin.NewController(
            paaTrustStorePath=str(paa_root_cert_dir)
        )
        LOGGER.debug("CHIP Device Controller Initialized")

    def _get_node_lock(self, node_id: int) -> asyncio.Lock:
        """Return lock for given node."""
        if node_id not in self._node_lock:
            self._node_lock[node_id] = asyncio.Lock()
        return self._node_lock[node_id]

    async def _call_sdk_executor(
        self,
        executor: ThreadPoolExecutor | None,
        target: Callable[..., _T],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        """Call function on the SDK in executor and return result."""
        if self.server.loop is None:
            raise RuntimeError("Server not started.")

        return cast(
            _T,
            await self.server.loop.run_in_executor(
                executor,
                partial(target, *args, **kwargs),
            ),
        )

    async def _call_sdk(
        self,
        target: Callable[..., _T],
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        return await self._call_sdk_executor(None, target, *args, **kwargs)

    @lru_cache(maxsize=1024)  # noqa: B019
    def get_node_logger(
        self, logger: logging.Logger, node_id: int
    ) -> logging.LoggerAdapter:
        """Return a logger for a specific node."""
        return logging.LoggerAdapter(logger, {"node": node_id})

    async def get_compressed_fabric_id(self) -> int:
        """Get the compressed fabric id."""
        return await self._call_sdk(self._chip_controller.GetCompressedFabricId)

    async def shutdown(self) -> None:
        """Shutdown the device controller."""
        # unsubscribe all node subscriptions
        for sub in self._subscriptions.values():
            await self._call_sdk(sub.Shutdown)
        self._subscriptions = {}

        await self._call_sdk(self._chip_controller.Shutdown)

    async def commission_with_code(
        self,
        node_id: int,
        setup_payload: str,
        discovery_type: DiscoveryType,
    ) -> int:
        """Commission a device using a QR Code or Manual Pairing Code."""
        return cast(
            int,
            await self._chip_controller.CommissionWithCode(
                setupPayload=setup_payload,
                nodeid=node_id,
                discoveryType=discovery_type,
            ),
        )

    async def commission_on_network(
        self,
        node_id: int,
        setup_pin_code: int,
        disc_filter_type: FilterType = FilterType.NONE,
        disc_filter: Any = None,
    ) -> int:
        """Commission a device on the network."""
        return cast(
            int,
            await self._chip_controller.CommissionOnNetwork(
                nodeId=node_id,
                setupPinCode=setup_pin_code,
                filterType=disc_filter_type,
                filter=disc_filter,
            ),
        )

    async def commission_ip(
        self, node_id: int, setup_pin_code: int, ip_addr: str
    ) -> int:
        """Commission a device using an IP address."""
        return cast(
            int,
            await self._chip_controller.CommissionIP(
                nodeid=node_id,
                setupPinCode=setup_pin_code,
                ipaddr=ip_addr,
            ),
        )

    async def set_wifi_credentials(self, ssid: str, credentials: str) -> None:
        """Set WiFi credentials to use on commissioning."""
        await self._call_sdk(
            self._chip_controller.SetWiFiCredentials,
            ssid=ssid,
            credentials=credentials,
        )

    async def set_thread_operational_dataset(self, dataset: str) -> None:
        """Set Thread operational dataset to use on commissioning."""
        await self._call_sdk(
            self._chip_controller.SetThreadOperationalDataset,
            threadOperationalDataset=bytes.fromhex(dataset),
        )

    async def unpair_device(self, node_id: int) -> PyChipError:
        """Remove our fabric from given node.

        Tries to look up the device attached to our controller with the given
        remote node id and ask it to remove Fabric.
        """
        return await self._chip_controller.UnpairDevice(nodeid=node_id)

    async def open_commissioning_window(
        self,
        node_id: int,
        timeout: int,  # noqa: ASYNC109 timeout parameter required for native timeout
        iteration: int,
        discriminator: int,
        option: ChipDeviceController.CommissioningWindowPasscode,
    ) -> CommissioningParameters:
        """Open a commissioning window to commission a device present on this controller to another."""
        async with self._get_node_lock(node_id):
            return await self._chip_controller.OpenCommissioningWindow(
                nodeid=node_id,
                timeout=timeout,
                iteration=iteration,
                discriminator=discriminator,
                option=option,
            )

    async def discover_commissionable_nodes(
        self,
    ) -> (
        list[ChipDeviceController.CommissionableNode]
        | ChipDeviceController.CommissionableNode
        | None
    ):
        """Discover Commissionable Nodes (discovered on BLE or mDNS)."""
        return await self._chip_controller.DiscoverCommissionableNodes()

    async def read_attribute(
        self,
        node_id: int,
        attributes: list[
            None
            | tuple[()]  # Empty tuple, all wildcard
            | tuple[int]  # Endpoint
            |
            # Wildcard endpoint, Cluster id present
            tuple[type[Clusters.Cluster]]
            |
            # Wildcard endpoint, Cluster + Attribute present
            tuple[type[Clusters.ClusterAttributeDescriptor]]
            |
            # Wildcard attribute id
            tuple[int, type[Clusters.Cluster]]
            |
            # Concrete path
            tuple[int, type[Clusters.ClusterAttributeDescriptor]]
        ]
        | None = None,
        events: list[
            None
            | tuple[()]  # Empty tuple, all wildcard
            | tuple[str, int]  # all wildcard with urgency set
            | tuple[int, int]  # Endpoint,
            |
            # Wildcard endpoint, Cluster id present
            tuple[type[Clusters.Cluster], int]
            |
            # Wildcard endpoint, Cluster + Event present
            tuple[type[Clusters.ClusterEvent], int]
            |
            # Wildcard event id
            tuple[int, type[Clusters.Cluster], int]
            |
            # Concrete path
            tuple[int, type[Clusters.ClusterEvent], int]
        ]
        | None = None,
        return_cluster_objects: bool = False,
        report_interval: tuple[int, int] | None = None,
        fabric_filtered: bool = True,
        auto_resubscribe: bool = True,
    ) -> (
        Attribute.SubscriptionTransaction
        | Attribute.AsyncReadTransaction.ReadResponse
        | None
    ):
        """Read an attribute on a node."""
        async with self._get_node_lock(node_id):
            result = await self._chip_controller.Read(
                nodeid=node_id,
                attributes=attributes,
                events=events,
                returnClusterObject=return_cluster_objects,
                reportInterval=report_interval,
                fabricFiltered=fabric_filtered,
                autoResubscribe=auto_resubscribe,
            )

        if report_interval is None:
            return result

        if not isinstance(result, Attribute.SubscriptionTransaction):
            # Aborted setups result in ReadResult instead of SubscriptionTransaction
            # Probably a bug: https://github.com/project-chip/connectedhomeip/issues/33570
            LOGGER.warning("Subscription setup for node id %d failed.", node_id)
            return None

        # if we reach this point, it means the node could be resolved
        # and the initial subscription succeeded, mark the node available.
        self._subscriptions[node_id] = result
        return result

    async def send_command(
        self,
        node_id: int,
        endpoint_id: int,
        command: Any,
        response_type: Any | None = None,
        timed_request_timeout_ms: int | None = None,
        interaction_timeout_ms: int | None = None,
    ) -> Any:
        """Send a command to a Matter node/device."""
        async with self._get_node_lock(node_id):
            return await self._chip_controller.SendCommand(
                nodeid=node_id,
                endpoint=endpoint_id,
                payload=command,
                responseType=response_type,
                timedRequestTimeoutMs=timed_request_timeout_ms,
                interactionTimeoutMs=interaction_timeout_ms,
            )

    async def read(
        self,
        node_id: int,
        attributes: list[Attribute.AttributePath],
        fabric_filtered: bool = True,
    ) -> Attribute.AsyncReadTransaction.ReadResponse:
        """Read a list of attributes and/or events from a target node."""
        if TYPE_CHECKING:
            assert self.server.loop

        # Read a list of attributes and/or events from a target node.
        # This is basically a re-implementation of the chip controller's Read function
        # but one that allows us to send/request custom attributes.
        future = self.server.loop.create_future()
        async with self._get_node_lock(node_id):
            # GetConnectedDevice is guaranteed to return a deviceProxy
            # otherwise it will raise a ChipStackError exception. A caller to
            # this function should handle the exception in any case, as the Read
            # below might raise such exceptions too.
            device = await self._chip_controller.GetConnectedDevice(
                nodeid=node_id,
                allowPASE=False,
                timeoutMs=None,
            )
            transaction = Attribute.AsyncReadTransaction(
                future, self.server.loop, self._chip_controller, True
            )
            Attribute.Read(
                transaction=transaction,
                device=device.deviceProxy,
                attributes=attributes,
                fabricFiltered=fabric_filtered,
            ).raise_on_error()
            await future
            return transaction.GetReadResponse()

    async def write_attribute(
        self,
        node_id: int,
        attributes: list[tuple[int, Clusters.ClusterAttributeDescriptor]],
    ) -> list[AttributeWriteResult] | None:
        """Write an attribute on a target node."""
        async with self._get_node_lock(node_id):
            result = await self._chip_controller.WriteAttribute(
                nodeid=node_id,
                attributes=attributes,
            )
        return cast(list[AttributeWriteResult], result)

    async def get_address_and_port(self, node_id: int) -> str:
        """Get the address and port of a node."""
        return await self._call_sdk(
            self._chip_controller.GetAddressAndPort, nodeid=node_id
        )

    async def find_or_establish_case_session(
        self, node_id: int, retries: int = 2
    ) -> DeviceProxyWrapper:
        """Attempt to establish a CASE session with target Node."""
        if self._chip_controller is None:
            raise RuntimeError("Device Controller not initialized.")

        node_logger = self.get_node_logger(LOGGER, node_id)
        attempt = 1

        while attempt <= retries:
            try:
                node_logger.log(
                    logging.DEBUG if attempt == 1 else logging.INFO,
                    "Attempting to establish CASE session... (attempt %s of %s)",
                    attempt,
                    retries,
                )
                time_start = time.time()
                async with self._get_node_lock(node_id):
                    return await self._chip_controller.GetConnectedDevice(
                        nodeid=node_id,
                        allowPASE=False,
                        timeoutMs=None,
                    )
            except ChipStackError as err:
                if attempt >= retries:
                    # when we're out of retries, raise NodeNotResolving
                    raise NodeNotResolving(
                        f"Unable to establish CASE session with Node {node_id}"
                    ) from err
                await asyncio.sleep(2 + attempt)
            finally:
                node_logger.debug(
                    "Establishing CASE session took %.1f seconds",
                    time.time() - time_start,
                )
            attempt += 1
        return None

    async def shutdown_subscription(self, node_id: int) -> None:
        """Shutdown a subscription for a node."""
        if sub := self._subscriptions.pop(node_id, None):
            await self._call_sdk(sub.Shutdown)

    async def subscription_override_liveness_timeout(
        self, node_id: int, liveness_timeout_ms: int
    ) -> None:
        """Override the liveness timeout for the subscription of the node."""
        if sub := self._subscriptions.get(node_id):
            await self._call_sdk(sub.OverrideLivenessTimeoutMs, liveness_timeout_ms)

    def node_has_subscription(self, node_id: int) -> bool:
        """Check if a node has an active subscription."""
        return node_id in self._subscriptions

    async def trigger_resubscribe_if_scheduled(self, node_id: int, reason: str) -> None:
        """Trigger resubscribe now if a resubscribe is scheduled.

        If the ReadClient currently has a resubscription attempt scheduled, This
        function allows to trigger that attempt immediately. This is useful
        when the server side is up and communicating, and it's a good time to
        try to resubscribe.
        """
        if sub := self._subscriptions.get(node_id, None):
            await sub.TriggerResubscribeIfScheduled(reason)
