"""Matter Device Controller implementation.

This module implements the Matter Device Controller WebSocket API. Compared to the
`ChipDeviceControllerWrapper` class it adds the WebSocket specific sauce and adds more
features which are not part of the Python Matter Device Controller per-se, e.g.
pinging a device.
"""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime
from functools import cached_property, lru_cache
import logging
import secrets
import time
from typing import TYPE_CHECKING, Any, cast

from chip.ChipDeviceCtrl import ChipDeviceController
from chip.clusters import Attribute, Objects as Clusters
from chip.clusters.Attribute import ValueDecodeFailure
from chip.clusters.ClusterObjects import ALL_ATTRIBUTES, ALL_CLUSTERS, Cluster
from chip.discovery import DiscoveryType
from chip.exceptions import ChipStackError
from chip.native import PyChipError
from zeroconf import BadTypeInNameException, IPVersion, ServiceStateChange, Zeroconf
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf

from matter_server.common.const import VERBOSE_LOG_LEVEL
from matter_server.common.custom_clusters import check_polled_attributes
from matter_server.common.models import (
    CommissionableNodeData,
    CommissioningParameters,
    MatterSoftwareVersion,
)
from matter_server.server.helpers.attributes import parse_attributes_from_read_result
from matter_server.server.helpers.utils import ping_ip
from matter_server.server.ota import check_for_update, load_local_updates
from matter_server.server.ota.provider import ExternalOtaProvider
from matter_server.server.sdk import ChipDeviceControllerWrapper

from ..common.errors import (
    InvalidArguments,
    NodeCommissionFailed,
    NodeInterviewFailed,
    NodeNotExists,
    NodeNotReady,
    NodeNotResolving,
    UpdateCheckError,
    UpdateError,
)
from ..common.helpers.api import api_command
from ..common.helpers.json import JSON_DECODE_EXCEPTIONS, json_loads
from ..common.helpers.util import (
    create_attribute_path_from_attribute,
    dataclass_from_dict,
    parse_attribute_path,
    parse_value,
)
from ..common.models import (
    APICommand,
    EventType,
    MatterNodeData,
    MatterNodeEvent,
    NodePingResult,
    UpdateSource,
)
from .const import DATA_MODEL_SCHEMA_VERSION

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path

    from .server import MatterServer

DATA_KEY_NODES = "nodes"
DATA_KEY_LAST_NODE_ID = "last_node_id"

LOGGER = logging.getLogger(__name__)
NODE_SUBSCRIPTION_FLOOR_DEFAULT = 1
NODE_SUBSCRIPTION_FLOOR_ICD = 0
NODE_SUBSCRIPTION_CEILING_WIFI = 60
NODE_SUBSCRIPTION_CEILING_THREAD = 60
NODE_SUBSCRIPTION_CEILING_BATTERY_POWERED = 600
NODE_RESUBSCRIBE_ATTEMPTS_UNAVAILABLE = 2
NODE_RESUBSCRIBE_TIMEOUT_OFFLINE = 30 * 60
NODE_RESUBSCRIBE_FORCE_TIMEOUT = 5
NODE_PING_TIMEOUT = 10
NODE_PING_TIMEOUT_BATTERY_POWERED = 60
NODE_MDNS_SUBSCRIPTION_RETRY_TIMEOUT = 30 * 60
CUSTOM_ATTRIBUTES_POLLER_INTERVAL = 30

MDNS_TYPE_OPERATIONAL_NODE = "_matter._tcp.local."
MDNS_TYPE_COMMISSIONABLE_NODE = "_matterc._udp.local."

TEST_NODE_START = 900000

ROUTING_ROLE_ATTRIBUTE_PATH = create_attribute_path_from_attribute(
    0, Clusters.ThreadNetworkDiagnostics.Attributes.RoutingRole
)
DESCRIPTOR_PARTS_LIST_ATTRIBUTE_PATH = create_attribute_path_from_attribute(
    0, Clusters.Descriptor.Attributes.PartsList
)
BASIC_INFORMATION_VENDOR_ID_ATTRIBUTE_PATH = create_attribute_path_from_attribute(
    0, Clusters.BasicInformation.Attributes.VendorID
)
BASIC_INFORMATION_PRODUCT_ID_ATTRIBUTE_PATH = create_attribute_path_from_attribute(
    0, Clusters.BasicInformation.Attributes.ProductID
)
BASIC_INFORMATION_SOFTWARE_VERSION_ATTRIBUTE_PATH = (
    create_attribute_path_from_attribute(
        0, Clusters.BasicInformation.Attributes.SoftwareVersion
    )
)
BASIC_INFORMATION_SOFTWARE_VERSION_STRING_ATTRIBUTE_PATH = (
    create_attribute_path_from_attribute(
        0, Clusters.BasicInformation.Attributes.SoftwareVersionString
    )
)
ICD_ATTR_LIST_ATTRIBUTE_PATH = create_attribute_path_from_attribute(
    0, Clusters.IcdManagement.Attributes.AttributeList
)


# pylint: disable=too-many-lines,too-many-instance-attributes,too-many-public-methods


class MatterDeviceController:
    """Class that manages the Matter devices."""

    def __init__(
        self,
        server: MatterServer,
        paa_root_cert_dir: Path,
        ota_provider_dir: Path,
    ):
        """Initialize the device controller."""
        self.server = server
        self._ota_provider_dir = ota_provider_dir

        self._chip_device_controller = ChipDeviceControllerWrapper(
            server, paa_root_cert_dir
        )

        # we keep the last events in memory so we can include them in the diagnostics dump
        self.event_history: deque[Attribute.EventReadResult] = deque(maxlen=25)
        self._compressed_fabric_id: int | None = None
        self._fabric_id_hex: str | None = None
        self._wifi_credentials_set: bool = False
        self._thread_credentials_set: bool = False
        self._setup_node_tasks = dict[int, asyncio.Task]()
        self._nodes_in_ota: set[int] = set()
        self._node_last_seen_on_mdns: dict[int, float] = {}
        self._nodes: dict[int, MatterNodeData] = {}
        self._last_known_ip_addresses: dict[int, list[str]] = {}
        self._resubscription_attempt: dict[int, int] = {}
        self._first_resubscribe_attempt: dict[int, float] = {}
        self._known_commissioning_params: dict[int, CommissioningParameters] = {}
        self._known_commissioning_params_timers: dict[int, asyncio.TimerHandle] = {}
        self._aiobrowser: AsyncServiceBrowser | None = None
        self._aiozc: AsyncZeroconf | None = None
        self._thread_node_setup_throttle = asyncio.Semaphore(5)
        self._mdns_event_timer: dict[str, asyncio.TimerHandle] = {}
        self._polled_attributes: dict[int, set[str]] = {}
        self._custom_attribute_poller_timer: asyncio.TimerHandle | None = None
        self._custom_attribute_poller_task: asyncio.Task | None = None
        self._attribute_update_callbacks: dict[int, list[Callable]] = {}

    async def initialize(self) -> None:
        """Initialize the device controller."""
        self._compressed_fabric_id = (
            await self._chip_device_controller.get_compressed_fabric_id()
        )
        self._fabric_id_hex = hex(self._compressed_fabric_id)[2:]
        await load_local_updates(self._ota_provider_dir)

    async def start(self) -> None:
        """Handle logic on controller start."""
        # load nodes from persistent storage
        nodes: dict[str, dict | None] = self.server.storage.get(DATA_KEY_NODES, {})
        orphaned_nodes: set[str] = set()
        for node_id_str, node_dict in nodes.items():
            node_id = int(node_id_str)
            if node_dict is None:
                # Non-initialized (left-over) node from a failed commissioning attempt.
                # NOTE: This code can be removed in a future version
                # as this can no longer happen.
                orphaned_nodes.add(node_id_str)
                continue
            try:
                node = dataclass_from_dict(MatterNodeData, node_dict, strict=True)
            except (KeyError, ValueError):
                # constructing MatterNodeData from the cached dict is not possible,
                # revert to a fallback object and the node will be re-interviewed
                node = MatterNodeData(
                    node_id=node_id,
                    date_commissioned=node_dict.get(
                        "date_commissioned",
                        datetime(1970, 1, 1),
                    ),
                    last_interview=node_dict.get(
                        "last_interview",
                        datetime(1970, 1, 1),
                    ),
                    interview_version=0,
                )
            # always mark node as unavailable at startup until subscriptions are ready
            node.available = False
            self._nodes[node_id] = node
        # cleanup orhpaned nodes from storage
        for node_id_str in orphaned_nodes:
            self.server.storage.remove(DATA_KEY_NODES, node_id_str)
        LOGGER.info("Loaded %s nodes from stored configuration", len(self._nodes))
        # set-up mdns browser
        self._aiozc = AsyncZeroconf(ip_version=IPVersion.All)
        services = [MDNS_TYPE_OPERATIONAL_NODE, MDNS_TYPE_COMMISSIONABLE_NODE]
        self._aiobrowser = AsyncServiceBrowser(
            self._aiozc.zeroconf,
            services,
            handlers=[self._on_mdns_service_state_change],
        )

    async def stop(self) -> None:
        """Handle logic on server stop."""
        # shutdown (and cleanup) mdns browser
        if self._aiobrowser:
            await self._aiobrowser.async_cancel()
        if self._aiozc:
            await self._aiozc.async_close()
        # Ensure any in-progress setup tasks are cancelled
        for task in self._setup_node_tasks.values():
            task.cancel()

        # shutdown the sdk device controller
        await self._chip_device_controller.shutdown()
        LOGGER.debug("Stopped.")

    @property
    def compressed_fabric_id(self) -> int | None:
        """Return the compressed fabric id."""
        return self._compressed_fabric_id

    @property
    def wifi_credentials_set(self) -> bool:
        """Return if WiFi credentials have been set."""
        return self._wifi_credentials_set

    @property
    def thread_credentials_set(self) -> bool:
        """Return if Thread operational dataset as been set."""
        return self._thread_credentials_set

    @cached_property
    def _loop(self) -> asyncio.AbstractEventLoop:
        """Return the event loop."""
        assert self.server.loop
        return self.server.loop

    @lru_cache(maxsize=1024)  # noqa: B019
    def get_node_logger(
        self, logger: logging.Logger, node_id: int
    ) -> logging.LoggerAdapter:
        """Return a logger for a specific node."""
        return logging.LoggerAdapter(logger, {"node": node_id})

    @api_command(APICommand.GET_NODES)
    def get_nodes(self, only_available: bool = False) -> list[MatterNodeData]:
        """Return all Nodes known to the server."""
        return [
            x
            for x in self._nodes.values()
            if x is not None and (x.available or not only_available)
        ]

    @api_command(APICommand.GET_NODE)
    def get_node(self, node_id: int) -> MatterNodeData:
        """Return info of a single Node."""
        if node := self._nodes.get(node_id):
            return node
        raise NodeNotExists(f"Node {node_id} does not exist or is not yet interviewed")

    @api_command(APICommand.COMMISSION_WITH_CODE)
    async def commission_with_code(
        self, code: str, network_only: bool = False
    ) -> MatterNodeData:
        """
        Commission a device using a QR Code or Manual Pairing Code.

        :param code: The QR Code or Manual Pairing Code for device commissioning.
        :param network_only: If True, restricts device discovery to network only.

        :return: The NodeInfo of the commissioned device.
        """
        if not network_only and not self.server.bluetooth_enabled:
            raise NodeCommissionFailed("Bluetooth commissioning is not available.")

        node_id = self._get_next_node_id()
        LOGGER.info(
            "Starting Matter commissioning with code using Node ID %s.",
            node_id,
        )
        try:
            commissioned_node_id: int = (
                await self._chip_device_controller.commission_with_code(
                    node_id,
                    code,
                    DiscoveryType.DISCOVERY_NETWORK_ONLY
                    if network_only
                    else DiscoveryType.DISCOVERY_ALL,
                )
            )
            # We use SDK default behavior which always uses the commissioning Node ID in the
            # generated NOC. So this should be the same really.
            LOGGER.info("Commissioned Node ID: %s vs %s", commissioned_node_id, node_id)
            if commissioned_node_id != node_id:
                raise RuntimeError("Returned Node ID must match requested Node ID")
        except ChipStackError as err:
            raise NodeCommissionFailed(
                f"Commission with code failed for node {node_id}."
            ) from err

        LOGGER.info("Matter commissioning of Node ID %s successful.", node_id)

        # perform full (first) interview of the device
        # we retry the interview max 3 times as it may fail in noisy
        # RF environments (in case of thread), mdns trouble or just flaky devices.
        # retrying both the mdns resolve and (first) interview, increases the chances
        # of a successful device commission.
        retries = 3
        while retries:
            try:
                await self.interview_node(node_id)
            except (NodeNotResolving, NodeInterviewFailed) as err:
                if retries <= 0:
                    raise err
                retries -= 1
                LOGGER.warning("Unable to interview Node %s: %s", node_id, err)
                await asyncio.sleep(5)
            else:
                break

        # make sure we start a subscription for this newly added node
        if task := self._setup_node_create_task(node_id):
            await task
        LOGGER.info("Commissioning of Node ID %s completed.", node_id)
        # return full node object once we're complete
        return self.get_node(node_id)

    @api_command(APICommand.COMMISSION_ON_NETWORK)
    async def commission_on_network(
        self,
        setup_pin_code: int,
        filter_type: int = 0,
        filter: Any = None,  # pylint: disable=redefined-builtin
        ip_addr: str | None = None,
    ) -> MatterNodeData:
        """
        Do the routine for OnNetworkCommissioning, with a filter for mDNS discovery.

        The filter can be an integer,
        a string or None depending on the actual type of selected filter.

        NOTE: For advanced usecases only, use `commission_with_code`
        for regular commissioning.

        Returns full NodeInfo once complete.
        """
        node_id = self._get_next_node_id()
        if ip_addr is not None:
            ip_addr = self.server.scope_ipv6_lla(ip_addr)

        try:
            if ip_addr is None:
                # regular CommissionOnNetwork if no IP address provided
                LOGGER.info(
                    "Starting Matter commissioning on network using Node ID %s.",
                    node_id,
                )
                commissioned_node_id = (
                    await self._chip_device_controller.commission_on_network(
                        node_id, setup_pin_code, filter_type, filter
                    )
                )
            else:
                LOGGER.info(
                    "Starting Matter commissioning using Node ID %s and IP %s.",
                    node_id,
                    ip_addr,
                )
                commissioned_node_id = await self._chip_device_controller.commission_ip(
                    node_id, setup_pin_code, ip_addr
                )
            # We use SDK default behavior which always uses the commissioning Node ID in the
            # generated NOC. So this should be the same really.
            if commissioned_node_id != node_id:
                raise RuntimeError("Returned Node ID must match requested Node ID")
        except ChipStackError as err:
            raise NodeCommissionFailed(
                f"Commissioning failed for node {node_id}."
            ) from err

        LOGGER.info("Matter commissioning of Node ID %s successful.", node_id)

        # perform full (first) interview of the device
        # we retry the interview max 3 times as it may fail in noisy
        # RF environments (in case of thread), mdns trouble or just flaky devices.
        # retrying both the mdns resolve and (first) interview, increases the chances
        # of a successful device commission.
        retries = 3
        while retries:
            try:
                await self.interview_node(node_id)
            except NodeInterviewFailed as err:
                if retries <= 0:
                    raise err
                retries -= 1
                LOGGER.warning("Unable to interview Node %s: %s", node_id, err)
                await asyncio.sleep(5)
            else:
                break
        # make sure we start a subscription for this newly added node
        if task := self._setup_node_create_task(node_id):
            await task
        LOGGER.info("Commissioning of Node ID %s completed.", node_id)
        # return full node object once we're complete
        return self.get_node(node_id)

    @api_command(APICommand.SET_WIFI_CREDENTIALS)
    async def set_wifi_credentials(self, ssid: str, credentials: str) -> None:
        """Set WiFi credentials for commissioning to a (new) device."""

        await self._chip_device_controller.set_wifi_credentials(ssid, credentials)
        self._wifi_credentials_set = True
        self.server.signal_event(EventType.SERVER_INFO_UPDATED, self.server.get_info())

    @api_command(APICommand.SET_THREAD_DATASET)
    async def set_thread_operational_dataset(self, dataset: str) -> None:
        """Set Thread Operational dataset in the stack."""

        await self._chip_device_controller.set_thread_operational_dataset(dataset)
        self._thread_credentials_set = True
        self.server.signal_event(EventType.SERVER_INFO_UPDATED, self.server.get_info())

    @api_command(APICommand.OPEN_COMMISSIONING_WINDOW)
    async def open_commissioning_window(
        self,
        node_id: int,
        timeout: int = 300,  # noqa: ASYNC109 timeout parameter required for native timeout
        iteration: int = 1000,
        option: int = ChipDeviceController.CommissioningWindowPasscode.kTokenWithRandomPin,
        discriminator: int | None = None,
    ) -> CommissioningParameters:
        """Open a commissioning window to commission a device present on this controller to another.

        Returns code to use as discriminator.
        """
        if (node := self._nodes.get(node_id)) is None or not node.available:
            raise NodeNotReady(f"Node {node_id} is not (yet) available.")

        read_response: Attribute.AsyncReadTransaction.ReadResponse = (
            await self._chip_device_controller.read_attribute(
                node_id,
                [(0, Clusters.AdministratorCommissioning.Attributes.WindowStatus)],
            )
        )
        window_status = cast(
            Clusters.AdministratorCommissioning.Enums.CommissioningWindowStatusEnum,
            read_response.attributes[0][Clusters.AdministratorCommissioning][
                Clusters.AdministratorCommissioning.Attributes.WindowStatus
            ],
        )

        if (
            window_status
            == Clusters.AdministratorCommissioning.Enums.CommissioningWindowStatusEnum.kWindowNotOpen
        ):
            # Commissioning window is no longer open (e.g. device got paired already)
            # Remove our stored commissioning parameters.
            if node_id in self._known_commissioning_params_timers:
                self._known_commissioning_params_timers[node_id].cancel()
            self._known_commissioning_params.pop(node_id, None)
        else:
            # Node is still in commissioning mode, return previous parameters
            if node_id in self._known_commissioning_params:
                return self._known_commissioning_params[node_id]

            # We restarted or somebody else put node into commissioning mode
            # Close commissioning window and put into commissioning mode again.
            LOGGER.info(
                "Commissioning window open but no parameters available. Closing and reopening commissioning window for node %s",
                node_id,
            )
            await self._chip_device_controller.send_command(
                node_id,
                endpoint_id=0,
                command=Clusters.AdministratorCommissioning.Commands.RevokeCommissioning(),
                timed_request_timeout_ms=5000,
            )

        if discriminator is None:
            discriminator = secrets.randbelow(2**12)

        sdk_result = await self._chip_device_controller.open_commissioning_window(
            node_id,
            timeout,
            iteration,
            discriminator,
            option,
        )
        self._known_commissioning_params[node_id] = params = CommissioningParameters(
            setup_pin_code=sdk_result.setupPinCode,
            setup_manual_code=sdk_result.setupManualCode,
            setup_qr_code=sdk_result.setupQRCode,
        )
        # we store the commission parameters and clear them after the timeout
        self._known_commissioning_params_timers[node_id] = self._loop.call_later(
            timeout, self._known_commissioning_params.pop, node_id, None
        )
        return params

    @api_command(APICommand.DISCOVER)
    async def discover_commissionable_nodes(
        self,
    ) -> list[CommissionableNodeData]:
        """Discover Commissionable Nodes (discovered on BLE or mDNS)."""
        sdk_result = await self._chip_device_controller.discover_commissionable_nodes()
        if sdk_result is None:
            return []
        # ensure list
        if not isinstance(sdk_result, list):
            sdk_result = [sdk_result]
        return [
            CommissionableNodeData(
                instance_name=x.instanceName,
                host_name=x.hostName,
                port=x.port,
                long_discriminator=x.longDiscriminator,
                vendor_id=x.vendorId,
                product_id=x.productId,
                commissioning_mode=x.commissioningMode,
                device_type=x.deviceType,
                device_name=x.deviceName,
                pairing_instruction=x.pairingInstruction,
                pairing_hint=x.pairingHint,
                mrp_retry_interval_idle=x.mrpRetryIntervalIdle,
                mrp_retry_interval_active=x.mrpRetryIntervalActive,
                supports_tcp=x.supportsTcp,
                addresses=x.addresses,
                rotating_id=x.rotatingId,
            )
            for x in sdk_result
        ]

    @api_command(APICommand.INTERVIEW_NODE)
    async def interview_node(self, node_id: int) -> None:
        """Interview a node."""
        if node_id >= TEST_NODE_START:
            LOGGER.debug(
                "interview_node called for test node %s",
                node_id,
            )
            self.server.signal_event(EventType.NODE_UPDATED, self._nodes[node_id])
            return

        try:
            LOGGER.info("Interviewing node: %s", node_id)
            read_response: Attribute.AsyncReadTransaction.ReadResponse = (
                await self._chip_device_controller.read_attribute(
                    node_id,
                    [()],
                    fabric_filtered=False,
                )
            )
        except ChipStackError as err:
            raise NodeInterviewFailed(f"Failed to interview node {node_id}") from err

        is_new_node = node_id not in self._nodes
        existing_info = self._nodes.get(node_id)
        node = MatterNodeData(
            node_id=node_id,
            date_commissioned=(
                existing_info.date_commissioned if existing_info else datetime.utcnow()
            ),
            last_interview=datetime.utcnow(),
            interview_version=DATA_MODEL_SCHEMA_VERSION,
            available=existing_info.available if existing_info else False,
            attributes=parse_attributes_from_read_result(read_response.tlvAttributes),
        )

        if existing_info:
            node.attribute_subscriptions = existing_info.attribute_subscriptions
        # work out if the node is a bridge device by looking at the devicetype of endpoint 1
        if attr_data := node.attributes.get("1/29/0"):
            node.is_bridge = any(x[0] == 14 for x in attr_data)

        # save updated node data
        self._nodes[node_id] = node
        self._write_node_state(node_id, True)
        if is_new_node:
            # new node - first interview
            self.server.signal_event(EventType.NODE_ADDED, node)
        else:
            # existing node, signal node updated event
            # TODO: maybe only signal this event if attributes actually changed ?
            self.server.signal_event(EventType.NODE_UPDATED, node)

        LOGGER.debug("Interview of node %s completed", node_id)

    @api_command(APICommand.DEVICE_COMMAND)
    async def send_device_command(
        self,
        node_id: int,
        endpoint_id: int,
        cluster_id: int,
        command_name: str,
        payload: dict,
        response_type: Any | None = None,
        timed_request_timeout_ms: int | None = None,
        interaction_timeout_ms: int | None = None,
    ) -> Any:
        """Send a command to a Matter node/device."""
        if (node := self._nodes.get(node_id)) is None or not node.available:
            raise NodeNotReady(f"Node {node_id} is not (yet) available.")
        cluster_cls: Cluster = ALL_CLUSTERS[cluster_id]
        command_cls = getattr(cluster_cls.Commands, command_name)
        command = dataclass_from_dict(command_cls, payload, allow_sdk_types=True)
        if node_id >= TEST_NODE_START:
            LOGGER.debug(
                "send_device_command called for test node %s on endpoint_id: %s - "
                "cluster_id: %s - command_name: %s - payload: %s\n%s",
                node_id,
                endpoint_id,
                cluster_id,
                command_name,
                payload,
                command,
            )
            return None
        return await self._chip_device_controller.send_command(
            node_id,
            endpoint_id,
            command,
            response_type,
            timed_request_timeout_ms,
            interaction_timeout_ms,
        )

    @api_command(APICommand.READ_ATTRIBUTE)
    async def read_attribute(
        self,
        node_id: int,
        attribute_path: str | list[str],
        fabric_filtered: bool = False,
    ) -> dict[str, Any]:
        """
        Read one or more attribute(s) on a node by specifying an attributepath.

        The attribute path can be a single string or a list of strings.
        The attribute path may contain wildcards (*) for cluster and/or attribute id.

        The return type is a dictionary with the attribute path as key and the value as value.
        """
        if (node := self._nodes.get(node_id)) is None or not node.available:
            raise NodeNotReady(f"Node {node_id} is not (yet) available.")
        attribute_paths = (
            attribute_path if isinstance(attribute_path, list) else [attribute_path]
        )

        # handle test node
        if node_id >= TEST_NODE_START:
            LOGGER.debug(
                "read_attribute called for test node %s on path(s): %s - fabric_filtered: %s",
                node_id,
                str(attribute_paths),
                fabric_filtered,
            )
            return {
                attr_path: self._nodes[node_id].attributes.get(attr_path)
                for attr_path in attribute_paths
            }

        LOGGER.debug(
            "read_attribute called for node %s on path(s): %s - fabric_filtered: %s",
            node_id,
            str(attribute_paths),
            fabric_filtered,
        )
        # parse text based attribute paths into the SDK Attribute Path objects
        attributes: list[Attribute.AttributePath] = []
        for attr_path in attribute_paths:
            endpoint_id, cluster_id, attribute_id = parse_attribute_path(attr_path)
            attributes.append(
                Attribute.AttributePath(
                    EndpointId=endpoint_id,
                    ClusterId=cluster_id,
                    AttributeId=attribute_id,
                )
            )

        result = await self._chip_device_controller.read(
            node_id,
            attributes,
            fabric_filtered,
        )
        read_atributes = parse_attributes_from_read_result(result.tlvAttributes)
        # update cached info in node attributes and signal events for updated attributes
        values_changed = False
        for attr_path, value in read_atributes.items():
            if node.attributes.get(attr_path) != value:
                node.attributes[attr_path] = value
                self.server.signal_event(
                    EventType.ATTRIBUTE_UPDATED,
                    # send data as tuple[node_id, attribute_path, new_value]
                    (node_id, attr_path, value),
                )

                values_changed = True
        # schedule writing of the node state if any values changed
        if values_changed:
            self._write_node_state(node_id)
        return read_atributes

    @api_command(APICommand.WRITE_ATTRIBUTE)
    async def write_attribute(
        self,
        node_id: int,
        attribute_path: str,
        value: Any,
    ) -> Any:
        """Write an attribute(value) on a target node."""
        if (node := self._nodes.get(node_id)) is None or not node.available:
            raise NodeNotReady(f"Node {node_id} is not (yet) available.")
        endpoint_id, cluster_id, attribute_id = parse_attribute_path(attribute_path)
        if endpoint_id is None:
            raise InvalidArguments(f"Invalid attribute path: {attribute_path}")
        attribute = cast(
            Clusters.ClusterAttributeDescriptor,
            ALL_ATTRIBUTES[cluster_id][attribute_id](),
        )
        attribute.value = parse_value(
            name=attribute_path,
            value=value,
            value_type=attribute.attribute_type.Type,
            allow_none=False,
            allow_sdk_types=True,
        )
        if node_id >= TEST_NODE_START:
            LOGGER.debug(
                "write_attribute called for test node %s on path %s - value %s\n%s",
                node_id,
                attribute_path,
                value,
                attribute,
            )
            return None
        return await self._chip_device_controller.write_attribute(
            node_id, [(endpoint_id, attribute)]
        )

    @api_command(APICommand.REMOVE_NODE)
    async def remove_node(self, node_id: int) -> None:
        """Remove a Matter node/device from the fabric."""
        if node_id not in self._nodes:
            raise NodeNotExists(
                f"Node {node_id} does not exist or has not been interviewed."
            )

        LOGGER.info("Removing Node ID %s.", node_id)

        if task := self._setup_node_tasks.pop(node_id, None):
            task.cancel()

        # shutdown any existing subscriptions
        await self._chip_device_controller.shutdown_subscription(node_id)
        self._polled_attributes.pop(node_id, None)

        node = self._nodes.pop(node_id)
        self.server.storage.remove(
            DATA_KEY_NODES,
            subkey=str(node_id),
        )

        LOGGER.info("Node ID %s successfully removed from Matter server.", node_id)

        self.server.signal_event(EventType.NODE_REMOVED, node_id)

        if node is None or node_id >= TEST_NODE_START:
            return

        try:
            await self._chip_device_controller.unpair_device(node_id)
        except ChipStackError as err:
            LOGGER.warning("Removing current fabric from device failed: %s", err)

    @api_command(APICommand.PING_NODE)
    async def ping_node(self, node_id: int, attempts: int = 1) -> NodePingResult:
        """Ping node on the currently known IP-address(es)."""
        result: NodePingResult = {}
        if node_id >= TEST_NODE_START:
            return {"0.0.0.0": True, "0000:1111:2222:3333:4444": True}
        node = self._nodes.get(node_id)
        if node is None:
            raise NodeNotExists(
                f"Node {node_id} does not exist or is not yet interviewed"
            )
        node_logger = self.get_node_logger(LOGGER, node_id)

        battery_powered = (
            node.attributes.get(ROUTING_ROLE_ATTRIBUTE_PATH, 0)
            == Clusters.ThreadNetworkDiagnostics.Enums.RoutingRoleEnum.kSleepyEndDevice
        )

        async def _do_ping(ip_address: str) -> None:
            """Ping IP and add to result."""
            timeout = (
                NODE_PING_TIMEOUT_BATTERY_POWERED
                if battery_powered
                else NODE_PING_TIMEOUT
            )
            if "%" in ip_address:
                # ip address contains an interface index
                clean_ip, interface_idx = ip_address.split("%", 1)
                node_logger.debug(
                    "Pinging address %s (using interface %s)", clean_ip, interface_idx
                )
            else:
                node_logger.debug("Pinging address %s", ip_address)
            result[ip_address] = await ping_ip(ip_address, timeout, attempts=attempts)

        ip_addresses = await self._get_node_ip_addresses(node_id, prefer_cache=False)
        tasks = [_do_ping(x) for x in ip_addresses]
        # TODO: replace this gather with a taskgroup once we bump our py version
        await asyncio.gather(*tasks)

        # retrieve the currently connected/used address which is used
        # by the sdk for communicating with the device
        if sdk_result := await self._chip_device_controller.get_address_and_port(
            node_id
        ):
            active_address = sdk_result[0]
            node_logger.info(
                "The SDK is communicating with the device using %s", active_address
            )
            if active_address not in result and node.available:
                # if the sdk is connected to a node, treat the address as pingable
                result[active_address] = True

        return result

    async def _get_node_ip_addresses(
        self, node_id: int, prefer_cache: bool = False
    ) -> list[str]:
        """Get the IP addresses of a node."""
        cached_info = self._last_known_ip_addresses.get(node_id, [])
        if prefer_cache and cached_info:
            return cached_info
        node = self._nodes.get(node_id)
        if node is None:
            raise NodeNotExists(
                f"Node {node_id} does not exist or is not yet interviewed"
            )
        node_logger = self.get_node_logger(LOGGER, node_id)
        # query mdns for all IP's
        # ensure both fabric id and node id have 16 characters (prefix with zero's)
        mdns_name = f"{self.compressed_fabric_id:0{16}X}-{node_id:0{16}X}.{MDNS_TYPE_OPERATIONAL_NODE}"
        info = AsyncServiceInfo(MDNS_TYPE_OPERATIONAL_NODE, mdns_name)
        if TYPE_CHECKING:
            assert self._aiozc is not None
        if not await info.async_request(self._aiozc.zeroconf, 3000):
            node_logger.info(
                "Node could not be discovered on the network, returning cached IP's"
            )
            return cached_info
        ip_addresses = info.parsed_scoped_addresses(IPVersion.All)
        # cache this info for later use
        self._last_known_ip_addresses[node_id] = ip_addresses
        return ip_addresses

    @api_command(APICommand.GET_NODE_IP_ADDRESSES)
    async def get_node_ip_addresses(
        self,
        node_id: int,
        prefer_cache: bool = False,
        scoped: bool = False,
    ) -> list[str]:
        """Return the currently known (scoped) IP-address(es)."""
        ip_addresses = await self._get_node_ip_addresses(node_id, prefer_cache)
        return ip_addresses if scoped else [x.split("%")[0] for x in ip_addresses]

    @api_command(APICommand.IMPORT_TEST_NODE)
    async def import_test_node(self, dump: str) -> None:
        """Import test node(s) from a HA or Matter server diagnostics dump."""
        try:
            dump_data = cast(dict, json_loads(dump))
        except JSON_DECODE_EXCEPTIONS as err:
            raise InvalidArguments("Invalid json") from err
        # the dump format we accept here is a Home Assistant diagnostics file
        # dump can either be a single dump or a full dump with multiple nodes
        dump_nodes: list[dict[str, Any]]
        if "node" in dump_data["data"]:
            dump_nodes = [dump_data["data"]["node"]]
        else:
            dump_nodes = dump_data["data"]["server"]["nodes"]
        # node ids > 900000 are reserved for test nodes
        if self._nodes:
            next_test_node_id = max(*(x for x in self._nodes), TEST_NODE_START) + 1
        else:
            # an empty self._nodes dict evaluates to false so we set the first
            # test node id to TEST_NODE_START
            next_test_node_id = TEST_NODE_START
        for node_dict in dump_nodes:
            node = dataclass_from_dict(MatterNodeData, node_dict, strict=True)
            node.node_id = next_test_node_id
            next_test_node_id += 1
            self._nodes[node.node_id] = node
            self.server.signal_event(EventType.NODE_ADDED, node)

    @api_command(APICommand.CHECK_NODE_UPDATE)
    async def check_node_update(self, node_id: int) -> MatterSoftwareVersion | None:
        """
        Check if there is an update for a particular node.

        Reads the current software version and checks the DCL if there is an update
        available. If there is an update available, the command returns the version
        information of the latest update available.
        """

        update_source, update = await self._check_node_update(node_id)
        if update_source is None or update is None:
            return None

        if not all(
            key in update
            for key in [
                "vid",
                "pid",
                "softwareVersion",
                "softwareVersionString",
                "minApplicableSoftwareVersion",
                "maxApplicableSoftwareVersion",
            ]
        ):
            raise UpdateCheckError("Invalid update data")

        return MatterSoftwareVersion(
            vid=update["vid"],
            pid=update["pid"],
            software_version=update["softwareVersion"],
            software_version_string=update["softwareVersionString"],
            firmware_information=update.get("firmwareInformation", None),
            min_applicable_software_version=update["minApplicableSoftwareVersion"],
            max_applicable_software_version=update["maxApplicableSoftwareVersion"],
            release_notes_url=update.get("releaseNotesUrl", None),
            update_source=update_source,
        )

    @api_command(APICommand.UPDATE_NODE)
    async def update_node(self, node_id: int, software_version: int | str) -> None:
        """
        Update a node to a new software version.

        This command checks if the requested software version is indeed still available
        and if so, it will start the update process. The update process will be handled
        by the built-in OTA provider. The OTA provider will download the update and
        notify the node about the new update.
        """

        node_logger = self.get_node_logger(LOGGER, node_id)
        node_logger.info("Update to software version %r", software_version)

        _, update = await self._check_node_update(node_id, software_version)
        if update is None:
            raise UpdateCheckError(
                f"Software version {software_version} is not available for node {node_id}."
            )

        # Add update to the OTA provider
        ota_provider = ExternalOtaProvider(
            self.server.vendor_id,
            self._ota_provider_dir,
            self._ota_provider_dir / f"{node_id}",
        )

        await ota_provider.initialize()

        node_logger.info("Downloading update from '%s'", update["otaUrl"])
        await ota_provider.fetch_update(update)

        self._attribute_update_callbacks.setdefault(node_id, []).append(
            ota_provider.check_update_state
        )

        try:
            if node_id in self._nodes_in_ota:
                raise UpdateError(
                    f"Node {node_id} is already in the process of updating."
                )

            self._nodes_in_ota.add(node_id)

            # Make sure any previous instances get stopped
            node_logger.info("Starting update using OTA Provider.")
            await ota_provider.start_update(
                self._chip_device_controller,
                node_id,
            )
        finally:
            self._attribute_update_callbacks[node_id].remove(
                ota_provider.check_update_state
            )
            self._nodes_in_ota.remove(node_id)

    async def _check_node_update(
        self,
        node_id: int,
        requested_software_version: int | str | None = None,
    ) -> tuple[UpdateSource, dict] | tuple[None, None]:
        node_logger = self.get_node_logger(LOGGER, node_id)
        node = self._nodes[node_id]

        node_logger.debug("Check for updates.")
        vid = cast(int, node.attributes.get(BASIC_INFORMATION_VENDOR_ID_ATTRIBUTE_PATH))
        pid = cast(
            int, node.attributes.get(BASIC_INFORMATION_PRODUCT_ID_ATTRIBUTE_PATH)
        )
        software_version = cast(
            int, node.attributes.get(BASIC_INFORMATION_SOFTWARE_VERSION_ATTRIBUTE_PATH)
        )
        software_version_string = node.attributes.get(
            BASIC_INFORMATION_SOFTWARE_VERSION_STRING_ATTRIBUTE_PATH
        )

        update_source, update = await check_for_update(
            node_logger, vid, pid, software_version, requested_software_version
        )
        if not update_source or not update:
            node_logger.info("No new update found.")
            return None, None

        if "otaUrl" not in update or update["otaUrl"].strip() == "":
            raise UpdateCheckError("Update found, but no OTA URL provided.")

        node_logger.info(
            "New software update found: %s on %s (current %s).",
            update["softwareVersionString"],
            update_source,
            software_version_string,
        )
        return update_source, update

    async def _subscribe_node(self, node_id: int) -> None:
        """
        Subscribe to all node state changes/events for an individual node.

        Note that by using the listen command at server level,
        you will receive all (subscribed) node events and attribute updates.
        """
        # pylint: disable=too-many-locals,too-many-statements
        if self._nodes.get(node_id) is None:
            raise NodeNotExists(
                f"Node {node_id} does not exist or has not been interviewed."
            )

        node_logger = self.get_node_logger(LOGGER, node_id)

        # Shutdown existing subscriptions for this node first
        await self._chip_device_controller.shutdown_subscription(node_id)

        def attribute_updated_callback(
            path: Attribute.AttributePath,
            old_value: Any,
            new_value: Any,
        ) -> None:
            node_logger.log(
                VERBOSE_LOG_LEVEL,
                "Attribute updated: %s - old value: %s - new value: %s",
                path,
                old_value,
                new_value,
            )

            # work out added/removed endpoints on bridges
            node = self._nodes[node_id]
            if node.is_bridge and str(path) == DESCRIPTOR_PARTS_LIST_ATTRIBUTE_PATH:
                endpoints_removed = set(old_value or []) - set(new_value)
                endpoints_added = set(new_value) - set(old_value or [])
                if endpoints_removed:
                    self._handle_endpoints_removed(node_id, endpoints_removed)
                if endpoints_added:
                    self._loop.create_task(
                        self._handle_endpoints_added(node_id, endpoints_added)
                    )
                return

            # work out if software version changed
            if (
                str(path) == BASIC_INFORMATION_SOFTWARE_VERSION_ATTRIBUTE_PATH
                and new_value != old_value
            ):
                # schedule a full interview of the node if the software version changed
                self._loop.create_task(self.interview_node(node_id))

            # store updated value in node attributes
            node.attributes[str(path)] = new_value

            # schedule save to persistent storage
            self._write_node_state(node_id)

            if node_id in self._attribute_update_callbacks:
                for callback in self._attribute_update_callbacks[node_id]:
                    self._loop.create_task(callback(path, old_value, new_value))

            # This callback is running in the CHIP stack thread
            self.server.signal_event(
                EventType.ATTRIBUTE_UPDATED,
                # send data as tuple[node_id, attribute_path, new_value]
                (node_id, str(path), new_value),
            )

        def attribute_updated_callback_threadsafe(
            path: Attribute.AttributePath,
            transaction: Attribute.SubscriptionTransaction,
        ) -> None:
            new_value = transaction.GetTLVAttribute(path)
            # failsafe: ignore ValueDecodeErrors
            # these are set by the SDK if parsing the value failed miserably
            if isinstance(new_value, ValueDecodeFailure):
                return

            node = self._nodes[node_id]
            old_value = node.attributes.get(str(path))

            # return early if the value did not actually change at all
            if old_value == new_value:
                return

            self._loop.call_soon_threadsafe(
                attribute_updated_callback, path, old_value, new_value
            )

        def event_callback(
            data: Attribute.EventReadResult,
            transaction: Attribute.SubscriptionTransaction,
        ) -> None:
            node_logger.log(
                VERBOSE_LOG_LEVEL,
                "Received node event: %s - transaction: %s",
                data,
                transaction,
            )
            node_event = MatterNodeEvent(
                node_id=node_id,
                endpoint_id=data.Header.EndpointId,
                cluster_id=data.Header.ClusterId,
                event_id=data.Header.EventId,
                event_number=data.Header.EventNumber,
                priority=data.Header.Priority,
                timestamp=data.Header.Timestamp,
                timestamp_type=data.Header.TimestampType,
                data=data.Data,
            )
            self.event_history.append(node_event)

            if isinstance(data.Data, Clusters.BasicInformation.Events.ShutDown):
                # Force resubscription after a shutdown event. Otherwise we'd have to
                # wait for up to NODE_SUBSCRIPTION_CEILING_BATTERY_POWERED minutes for
                # the SDK to notice the device is gone.
                self._node_unavailable(node_id, True)

            self.server.signal_event(EventType.NODE_EVENT, node_event)

        def event_callback_threadsafe(
            data: Attribute.EventReadResult,
            transaction: Attribute.SubscriptionTransaction,
        ) -> None:
            self._loop.call_soon_threadsafe(event_callback, data, transaction)

        def error_callback(
            chipError: int, transaction: Attribute.SubscriptionTransaction
        ) -> None:
            # pylint: disable=unused-argument, invalid-name
            node_logger.error("Got error from node: %s", chipError)

        def resubscription_attempted(
            transaction: Attribute.SubscriptionTransaction,
            terminationError: int,
            nextResubscribeIntervalMsec: int,
        ) -> None:
            # pylint: disable=unused-argument, invalid-name
            resubscription_attempt = self._resubscription_attempt[node_id]
            node_logger.info(
                "Subscription failed with %s, resubscription attempt %s",
                str(PyChipError(code=terminationError)),
                resubscription_attempt,
            )
            self._resubscription_attempt[node_id] = resubscription_attempt + 1
            if resubscription_attempt == 0:
                self._first_resubscribe_attempt[node_id] = time.time()
            # Mark node as unavailable and signal consumers.
            # We debounce it a bit so we only mark the node unavailable
            # after some resubscription attempts.
            if resubscription_attempt >= NODE_RESUBSCRIBE_ATTEMPTS_UNAVAILABLE:
                self._node_unavailable(node_id)
            # Shutdown the subscription if we tried to resubscribe for more than 30
            # minutes (typical TTL of mDNS). We assume this device got powered off.
            # When the device gets powered on again, it typically announces itself via
            # mDNS again. The mDNS browsing code will setup the subscription again.
            if (
                time.time() - self._first_resubscribe_attempt[node_id]
                > NODE_RESUBSCRIBE_TIMEOUT_OFFLINE
            ):
                asyncio.create_task(self._node_offline(node_id))

        def resubscription_succeeded(
            transaction: Attribute.SubscriptionTransaction,
        ) -> None:
            # pylint: disable=unused-argument, invalid-name
            node_logger.info("Re-Subscription succeeded")
            self._resubscription_attempt[node_id] = 0
            self._first_resubscribe_attempt.pop(node_id, None)
            # mark node as available and signal consumers
            node = self._nodes[node_id]
            if not node.available:
                node.available = True
                self.server.signal_event(EventType.NODE_UPDATED, node)

        node_logger.info("Setting up attributes and events subscription.")
        # determine subscription ceiling based on routing role
        # Endpoint 0, ThreadNetworkDiagnostics Cluster, routingRole attribute
        # for WiFi devices, this cluster doesn't exist.
        node = self._nodes[node_id]
        routing_role = node.attributes.get(ROUTING_ROLE_ATTRIBUTE_PATH)
        if routing_role is None:
            interval_ceiling = NODE_SUBSCRIPTION_CEILING_WIFI
        elif (
            routing_role
            == Clusters.ThreadNetworkDiagnostics.Enums.RoutingRoleEnum.kSleepyEndDevice
        ):
            interval_ceiling = NODE_SUBSCRIPTION_CEILING_BATTERY_POWERED
        else:
            interval_ceiling = NODE_SUBSCRIPTION_CEILING_THREAD
        if node.attributes.get(ICD_ATTR_LIST_ATTRIBUTE_PATH) is not None:
            # for ICD devices, the interval floor must be 0 according to the spec,
            # to prevent additional battery drainage. See Matter core spec, chapter 8.5.2.2.
            # TODO: revisit this after Matter 1.4 release (as that mighht change this again).
            interval_floor = NODE_SUBSCRIPTION_FLOOR_ICD
        else:
            interval_floor = NODE_SUBSCRIPTION_FLOOR_DEFAULT
        self._resubscription_attempt[node_id] = 0
        # set-up the actual subscription
        sub: Attribute.SubscriptionTransaction = (
            await self._chip_device_controller.read_attribute(
                node_id,
                [()],
                events=[("*", 1)],
                return_cluster_objects=False,
                report_interval=(interval_floor, interval_ceiling),
                auto_resubscribe=True,
            )
        )

        # Make sure to clear default handler which prints to stdout
        sub.SetAttributeUpdateCallback(None)
        sub.SetRawAttributeUpdateCallback(attribute_updated_callback_threadsafe)
        sub.SetEventUpdateCallback(event_callback_threadsafe)
        sub.SetErrorCallback(error_callback)
        sub.SetResubscriptionAttemptedCallback(resubscription_attempted)
        sub.SetResubscriptionSucceededCallback(resubscription_succeeded)

        node.available = True
        # update attributes with current state from read request
        tlv_attributes = sub.GetTLVAttributes()
        node.attributes.update(parse_attributes_from_read_result(tlv_attributes))

        report_interval_floor, report_interval_ceiling = (
            sub.GetReportingIntervalsSeconds()
        )
        node_logger.info(
            "Subscription succeeded with report interval [%d, %d]",
            report_interval_floor,
            report_interval_ceiling,
        )

        self.server.signal_event(EventType.NODE_UPDATED, node)

    def _get_next_node_id(self) -> int:
        """Return next node_id."""
        next_node_id = cast(int, self.server.storage.get(DATA_KEY_LAST_NODE_ID, 0)) + 1
        self.server.storage.set(DATA_KEY_LAST_NODE_ID, next_node_id, force=True)
        return next_node_id

    async def _setup_node_try_once(
        self,
        node_logger: logging.LoggerAdapter,
        node_id: int,
    ) -> None:
        """Handle set-up of subscriptions and interview (if needed) for known/discovered node."""
        node_data = self._nodes[node_id]
        is_thread_node = (
            node_data.attributes.get(ROUTING_ROLE_ATTRIBUTE_PATH) is not None
        )

        # use semaphore for thread based devices to (somewhat)
        # throttle the traffic that setup/initial subscription generates
        if is_thread_node:
            await self._thread_node_setup_throttle.acquire()

        try:
            node_logger.info("Setting-up node...")

            # try to resolve the node using the sdk first before do anything else
            try:
                await self._chip_device_controller.find_or_establish_case_session(
                    node_id=node_id
                )
            except NodeNotResolving as err:
                node_logger.warning(
                    "Setup for node failed: %s",
                    str(err) or err.__class__.__name__,
                    # log full stack trace if verbose logging is enabled
                    exc_info=err if LOGGER.isEnabledFor(VERBOSE_LOG_LEVEL) else None,
                )
                raise err

            # (re)interview node (only) if needed
            if (
                # re-interview if we dont have any node attributes (empty node)
                not node_data.attributes
                # re-interview if the data model schema has changed
                or node_data.interview_version != DATA_MODEL_SCHEMA_VERSION
            ):
                try:
                    await self.interview_node(node_id)
                except NodeInterviewFailed as err:
                    node_logger.warning(
                        "Setup for node failed: %s",
                        str(err) or err.__class__.__name__,
                        # log full stack trace if verbose logging is enabled
                        exc_info=err
                        if LOGGER.isEnabledFor(VERBOSE_LOG_LEVEL)
                        else None,
                    )
                    raise err

            # setup subscriptions for the node
            try:
                await self._subscribe_node(node_id)
            except ChipStackError as err:
                node_logger.warning(
                    "Unable to subscribe to Node: %s",
                    str(err) or err.__class__.__name__,
                    # log full stack trace if verbose logging is enabled
                    exc_info=err if LOGGER.isEnabledFor(VERBOSE_LOG_LEVEL) else None,
                )
                raise err

            # check if this node has any custom clusters that need to be polled
            if polled_attributes := check_polled_attributes(node_data):
                self._polled_attributes[node_id] = polled_attributes
                self._schedule_custom_attributes_poller()
        finally:
            if is_thread_node:
                self._thread_node_setup_throttle.release()

    async def _setup_node(self, node_id: int) -> None:
        if node_id not in self._nodes:
            raise NodeNotExists(f"Node {node_id} does not exist.")

        node_logger = self.get_node_logger(LOGGER, node_id)

        while True:
            try:
                await self._setup_node_try_once(node_logger, node_id)
                break
            except (NodeNotResolving, NodeInterviewFailed, ChipStackError):
                if (
                    time.time() - self._node_last_seen_on_mdns.get(node_id, 0)
                    > NODE_MDNS_SUBSCRIPTION_RETRY_TIMEOUT
                ):
                    # NOTE: assume the node will be picked up by mdns discovery later
                    # automatically when it becomes available again.
                    node_logger.warning(
                        "Node setup not completed after %s minutes, giving up.",
                        NODE_MDNS_SUBSCRIPTION_RETRY_TIMEOUT // 60,
                    )
                    break

            node_logger.info("Retrying node setup in 60 seconds...")
            await asyncio.sleep(60)

    def _setup_node_create_task(self, node_id: int) -> asyncio.Task | None:
        """Create a task for setting up a node with retry."""
        if node_id in self._setup_node_tasks:
            node_logger = self.get_node_logger(LOGGER, node_id)
            node_logger.debug("Setup task exists already for this Node")
            return None
        task = asyncio.create_task(self._setup_node(node_id))
        task.add_done_callback(lambda _: self._setup_node_tasks.pop(node_id, None))
        self._setup_node_tasks[node_id] = task
        return task

    def _handle_endpoints_removed(self, node_id: int, endpoints: Iterable[int]) -> None:
        """Handle callback for when bridge endpoint(s) get deleted."""
        node = self._nodes[node_id]
        for endpoint_id in endpoints:
            node.attributes = {
                key: value
                for key, value in node.attributes.items()
                if not key.startswith(f"{endpoint_id}/")
            }
            self.server.signal_event(
                EventType.ENDPOINT_REMOVED,
                {"node_id": node_id, "endpoint_id": endpoint_id},
            )
        # schedule save to persistent storage
        self._write_node_state(node_id)

    async def _handle_endpoints_added(
        self, node_id: int, endpoints: Iterable[int]
    ) -> None:
        """Handle callback for when bridge endpoint(s) get added."""
        # we simply do a full interview of the node
        await self.interview_node(node_id)
        # signal event to consumers
        for endpoint_id in endpoints:
            self.server.signal_event(
                EventType.ENDPOINT_ADDED,
                {"node_id": node_id, "endpoint_id": endpoint_id},
            )

    def _on_mdns_service_state_change(
        self,
        zeroconf: Zeroconf,  # pylint: disable=unused-argument
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        # mdns events may arrive in bursts of (duplicate) messages
        # so we debounce this with a timer handle.
        if state_change == ServiceStateChange.Removed:
            # if we have an existing timer for this name, cancel it.
            if cancel := self._mdns_event_timer.pop(name, None):
                cancel.cancel()
            if service_type == MDNS_TYPE_OPERATIONAL_NODE:
                # we're not interested in operational node removals,
                # this is already handled by the subscription logic
                return

        if name in self._mdns_event_timer:
            # We already have a timer to resolve this service, so ignore this callback.
            return

        if service_type == MDNS_TYPE_COMMISSIONABLE_NODE:
            # process the event with a debounce timer
            self._mdns_event_timer[name] = self._loop.call_later(
                0.5, self._on_mdns_commissionable_node_state, name, state_change
            )
            return

        if service_type == MDNS_TYPE_OPERATIONAL_NODE:
            if self._fabric_id_hex is None or self._fabric_id_hex not in name.lower():
                # filter out messages that are not for our fabric
                return
        # process the event with a debounce timer
        self._mdns_event_timer[name] = self._loop.call_later(
            0.5, self._on_mdns_operational_node_state, name, state_change
        )

    def _on_mdns_operational_node_state(
        self, name: str, state_change: ServiceStateChange
    ) -> None:
        """Handle a (operational) Matter node MDNS state change."""
        self._mdns_event_timer.pop(name, None)
        logger = LOGGER.getChild("mdns")
        # the mdns name is constructed as [fabricid]-[nodeid]._matter._tcp.local.
        # extract the node id from the name
        node_id = int(name.split("-")[1].split(".")[0], 16)
        node_logger = self.get_node_logger(logger, node_id)

        if not (node := self._nodes.get(node_id)):
            return  # this should not happen, but guard just in case

        self._node_last_seen_on_mdns[node_id] = time.time()

        # we only treat UPDATE state changes as ADD if the node is marked as
        # unavailable to ensure we catch a node being operational
        if node.available and state_change == ServiceStateChange.Updated:
            return

        if not self._chip_device_controller.node_has_subscription(node_id):
            node_logger.info("Discovered on mDNS")
            # Setup the node - this will setup the subscriptions etc.
            self._setup_node_create_task(node_id)
        elif state_change == ServiceStateChange.Added:
            # Trigger node re-subscriptions when mDNS entry got added
            # Note: Users seem to get such mDNS messages fairly regularly, and often
            # the subscription to the device is healthy and fine. This is not a problem
            # since trigger_resubscribe_if_scheduled won't do anything in that case
            # (no resubscribe is scheduled).
            # But this does speedup the resubscription process in case the subscription
            # is already in resubscribe mode.
            node_logger.debug("Activity on mDNS, trigger resubscribe if scheduled")
            asyncio.create_task(
                self._chip_device_controller.trigger_resubscribe_if_scheduled(
                    node_id, "mDNS state change detected"
                )
            )

    def _on_mdns_commissionable_node_state(
        self, name: str, state_change: ServiceStateChange
    ) -> None:
        """Handle a (commissionable) Matter node MDNS state change."""
        self._mdns_event_timer.pop(name, None)
        logger = LOGGER.getChild("mdns")

        try:
            info = AsyncServiceInfo(MDNS_TYPE_COMMISSIONABLE_NODE, name)
        except BadTypeInNameException as ex:
            logger.debug("Ignoring record with bad type in name: %s: %s", name, ex)
            return

        async def handle_commissionable_node_added() -> None:
            if TYPE_CHECKING:
                assert self._aiozc is not None
            await info.async_request(self._aiozc.zeroconf, 3000)
            logger.debug("Discovered commissionable Matter node: %s", info)

        if state_change == ServiceStateChange.Added:
            asyncio.create_task(handle_commissionable_node_added())
        elif state_change == ServiceStateChange.Removed:
            logger.debug("Commissionable Matter node disappeared: %s", info)

    def _write_node_state(self, node_id: int, force: bool = False) -> None:
        """Schedule the write of the current node state to persistent storage."""
        if node_id not in self._nodes:
            return  # guard
        if node_id >= TEST_NODE_START:
            return  # test nodes are stored in memory only
        node = self._nodes[node_id]
        self.server.storage.set(
            DATA_KEY_NODES,
            value=node,
            subkey=str(node_id),
            force=force,
        )

    def _node_unavailable(
        self, node_id: int, force_resubscription: bool = False
    ) -> None:
        """Mark node as unavailable."""
        # mark node as unavailable (if it wasn't already)
        node = self._nodes[node_id]
        if not node.available:
            return
        node.available = False
        self.server.signal_event(EventType.NODE_UPDATED, node)
        node_logger = self.get_node_logger(LOGGER, node_id)
        node_logger.info("Marked node as unavailable")
        if force_resubscription:
            # Make sure the subscriptions are expiring very soon to trigger subscription
            # resumption logic quickly. This is especially important for battery operated
            # devices so subscription resumption logic kicks in quickly.
            node_logger.info(
                "Forcing subscription timeout in %ds", NODE_RESUBSCRIBE_FORCE_TIMEOUT
            )
            asyncio.create_task(
                self._chip_device_controller.subscription_override_liveness_timeout(
                    node_id, NODE_RESUBSCRIBE_FORCE_TIMEOUT * 1000
                )
            )
            # Clear the timeout soon after the scheduled timeout above. This causes the
            # SDK to use the default liveness timeout again, which is what we want for
            # the once resumed subscription.
            self._loop.call_later(
                NODE_RESUBSCRIBE_FORCE_TIMEOUT + 1,
                lambda: asyncio.create_task(
                    self._chip_device_controller.subscription_override_liveness_timeout(
                        node_id, 0
                    )
                ),
            )

    async def _node_offline(self, node_id: int) -> None:
        """Mark node as offline."""
        # shutdown existing subscriptions
        node_logger = self.get_node_logger(LOGGER, node_id)
        node_logger.info("Node considered offline, shutdown subscription")
        await self._chip_device_controller.shutdown_subscription(node_id)

        # mark node as unavailable (if it wasn't already)
        self._node_unavailable(node_id)

    async def _custom_attributes_poller(self) -> None:
        """Poll custom clusters/attributes for changes."""
        for node_id in tuple(self._polled_attributes):
            node = self._nodes[node_id]
            if not node.available:
                continue
            attribute_paths = list(self._polled_attributes[node_id])
            try:
                # try to read the attribute(s) - this will fire an event if the value changed
                await self.read_attribute(
                    node_id, attribute_paths, fabric_filtered=False
                )
            except (ChipStackError, NodeNotReady) as err:
                LOGGER.warning(
                    "Polling custom attribute(s) %s for node %s failed: %s",
                    ",".join(attribute_paths),
                    node_id,
                    str(err) or err.__class__.__name__,
                    # log full stack trace if verbose logging is enabled
                    exc_info=err if LOGGER.isEnabledFor(VERBOSE_LOG_LEVEL) else None,
                )
            # polling attributes is heavy on network traffic, so we throttle it a bit
            await asyncio.sleep(2)
        # reschedule self to run at next interval
        self._schedule_custom_attributes_poller()

    def _schedule_custom_attributes_poller(self) -> None:
        """Schedule running the custom clusters/attributes poller at X interval."""
        if existing := self._custom_attribute_poller_timer:
            existing.cancel()

        def run_custom_attributes_poller() -> None:
            self._custom_attribute_poller_timer = None
            if (existing := self._custom_attribute_poller_task) and not existing.done():
                existing.cancel()
            self._custom_attribute_poller_task = asyncio.create_task(
                self._custom_attributes_poller()
            )

        # no need to schedule the poll if we have no (more) custom attributes to poll
        if not self._polled_attributes:
            return

        self._custom_attribute_poller_timer = self._loop.call_later(
            CUSTOM_ATTRIBUTES_POLLER_INTERVAL, run_custom_attributes_poller
        )
