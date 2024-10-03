"""Matter Client implementation."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Final, Optional, cast
import uuid

from chip.clusters import Objects as Clusters
from chip.clusters.Types import NullValue

from matter_server.common.errors import ERROR_MAP, NodeNotExists

from ..common.helpers.util import (
    convert_ip_address,
    convert_mac_address,
    create_attribute_path_from_attribute,
    dataclass_from_dict,
    dataclass_to_dict,
)
from ..common.models import (
    APICommand,
    CommandMessage,
    CommissionableNodeData,
    CommissioningParameters,
    ErrorResultMessage,
    EventMessage,
    EventType,
    MatterNodeData,
    MatterNodeEvent,
    MatterSoftwareVersion,
    MessageType,
    NodePingResult,
    ResultMessageBase,
    ServerDiagnostics,
    ServerInfoMessage,
    SuccessResultMessage,
)
from .connection import MatterClientConnection
from .exceptions import ConnectionClosed, InvalidState, ServerVersionTooOld
from .models.node import (
    MatterFabricData,
    MatterNode,
    NetworkType,
    NodeDiagnostics,
    NodeType,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

    from aiohttp import ClientSession
    from chip.clusters.Objects import ClusterCommand

SUB_WILDCARD: Final = "*"

# pylint: disable=too-many-public-methods,too-many-locals,too-many-branches


class MatterClient:
    """Manage a Matter server over WebSockets."""

    def __init__(self, ws_server_url: str, aiohttp_session: ClientSession):
        """Initialize the Client class."""
        self.connection = MatterClientConnection(ws_server_url, aiohttp_session)
        self.logger = logging.getLogger(__package__)
        self._nodes: dict[int, MatterNode] = {}
        self._result_futures: dict[str, asyncio.Future] = {}
        self._subscribers: dict[str, list[Callable[[EventType, Any], None]]] = {}
        self._stop_called: bool = False
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def server_info(self) -> ServerInfoMessage | None:
        """Return info of the server we're currently connected to."""
        return self.connection.server_info

    def subscribe_events(
        self,
        callback: Callable[[EventType, Any], None],
        event_filter: Optional[EventType] = None,
        node_filter: Optional[int] = None,
        attr_path_filter: Optional[str] = None,
    ) -> Callable[[], None]:
        """
        Subscribe to node and server events.

        Optionally filter by specific events or node attributes.
        Returns:
            function to unsubscribe.

        NOTE: To receive attribute changed events,
        you must also register the attributes to subscribe to
        with the `subscribe_attributes` method.
        """
        # for fast lookups we create a key based on the filters, allowing
        # a "catch all" with a wildcard (*).
        _event_filter: str
        if event_filter is None:
            _event_filter = SUB_WILDCARD
        else:
            _event_filter = event_filter.value

        _node_filter: str
        if node_filter is None:
            _node_filter = SUB_WILDCARD
        else:
            _node_filter = str(node_filter)

        if attr_path_filter is None:
            attr_path_filter = SUB_WILDCARD

        key = f"{_event_filter}/{_node_filter}/{attr_path_filter}"
        self._subscribers.setdefault(key, [])
        self._subscribers[key].append(callback)

        def unsubscribe() -> None:
            self._subscribers[key].remove(callback)

        return unsubscribe

    def get_nodes(self) -> list[MatterNode]:
        """Return all Matter nodes."""
        return list(self._nodes.values())

    def get_node(self, node_id: int) -> MatterNode:
        """Return Matter node by id or None if no node exists by that id."""
        if node := self._nodes.get(node_id):
            return node
        raise NodeNotExists(f"Node {node_id} does not exist or is not yet interviewed")

    async def commission_with_code(
        self, code: str, network_only: bool = False
    ) -> MatterNodeData:
        """
        Commission a device using a QR Code or Manual Pairing Code.

        :param code: The QR Code or Manual Pairing Code for device commissioning.
        :param network_only: If True, restricts device discovery to network only.

        :return: The NodeInfo of the commissioned device.
        """
        data = await self.send_command(
            APICommand.COMMISSION_WITH_CODE,
            require_schema=6 if network_only else None,
            code=code,
            network_only=network_only,
        )
        return dataclass_from_dict(MatterNodeData, data)

    async def commission_on_network(
        self, setup_pin_code: int, ip_addr: str | None = None
    ) -> MatterNodeData:
        """
        Do the routine for OnNetworkCommissioning.

        NOTE: For advanced usecases only, use `commission_with_code`
        for regular commissioning.

        Returns basic MatterNodeData once complete.
        """
        data = await self.send_command(
            APICommand.COMMISSION_ON_NETWORK,
            require_schema=6 if ip_addr is not None else None,
            setup_pin_code=setup_pin_code,
            ip_addr=ip_addr,
        )
        return dataclass_from_dict(MatterNodeData, data)

    async def set_wifi_credentials(self, ssid: str, credentials: str) -> None:
        """Set WiFi credentials for commissioning to a (new) device."""
        await self.send_command(
            APICommand.SET_WIFI_CREDENTIALS, ssid=ssid, credentials=credentials
        )

    async def set_thread_operational_dataset(self, dataset: str) -> None:
        """Set Thread Operational dataset in the stack."""
        await self.send_command(APICommand.SET_THREAD_DATASET, dataset=dataset)

    async def open_commissioning_window(
        self,
        node_id: int,
        timeout: int = 300,  # noqa: ASYNC109 timeout parameter required for native timeout
        iteration: int = 1000,
        option: int = 1,
        discriminator: Optional[int] = None,
    ) -> CommissioningParameters:
        """
        Open a commissioning window to commission a device present on this controller to another.

        Returns code to use as discriminator.
        """
        return dataclass_from_dict(
            CommissioningParameters,
            await self.send_command(
                APICommand.OPEN_COMMISSIONING_WINDOW,
                node_id=node_id,
                timeout=timeout,
                iteration=iteration,
                option=option,
                discriminator=discriminator,
            ),
        )

    async def discover_commissionable_nodes(
        self,
    ) -> list[CommissionableNodeData]:
        """Discover Commissionable Nodes (discovered on BLE or mDNS)."""
        return [
            dataclass_from_dict(CommissionableNodeData, x)
            for x in await self.send_command(APICommand.DISCOVER, require_schema=7)
        ]

    async def get_matter_fabrics(self, node_id: int) -> list[MatterFabricData]:
        """
        Get Matter fabrics from a device.

        Returns a list of MatterFabricData objects.
        """

        node = self.get_node(node_id)

        # refresh node's fabrics if the node is available so we have the latest info
        if node.available:
            await self.refresh_attribute(
                node_id,
                create_attribute_path_from_attribute(
                    0, Clusters.OperationalCredentials.Attributes.Fabrics
                ),
            )

        fabrics: list[
            Clusters.OperationalCredentials.Structs.FabricDescriptorStruct
        ] = node.get_attribute_value(
            0, None, Clusters.OperationalCredentials.Attributes.Fabrics
        )

        vendors_map = await self.send_command(
            APICommand.GET_VENDOR_NAMES,
            require_schema=3,
            filter_vendors=[f.vendorID for f in fabrics],
        )

        return [
            MatterFabricData(
                fabric_id=f.fabricID,
                vendor_id=f.vendorID,
                fabric_index=f.fabricIndex,
                fabric_label=f.label if f.label else None,
                vendor_name=vendors_map.get(str(f.vendorID)),
            )
            for f in fabrics
        ]

    async def remove_matter_fabric(self, node_id: int, fabric_index: int) -> None:
        """Remove Matter fabric from a device."""
        await self.send_device_command(
            node_id,
            0,
            Clusters.OperationalCredentials.Commands.RemoveFabric(
                fabricIndex=fabric_index,
            ),
        )

    async def ping_node(self, node_id: int) -> NodePingResult:
        """Ping node on the currently known IP-adress(es)."""
        return cast(
            NodePingResult,
            await self.send_command(APICommand.PING_NODE, node_id=node_id),
        )

    async def get_node_ip_addresses(
        self, node_id: int, prefer_cache: bool = True, scoped: bool = False
    ) -> list[str]:
        """Return the currently known (scoped) IP-address(es)."""
        if TYPE_CHECKING:
            assert self.server_info is not None
        if self.server_info.schema_version >= 8:
            return cast(
                list[str],
                await self.send_command(
                    APICommand.GET_NODE_IP_ADDRESSES,
                    require_schema=8,
                    node_id=node_id,
                    prefer_cache=prefer_cache,
                    scoped=scoped,
                ),
            )
        # alternative method of fetching ip addresses by enumerating NetworkInterfaces
        node = self.get_node(node_id)
        attribute = Clusters.GeneralDiagnostics.Attributes.NetworkInterfaces
        network_interface: Clusters.GeneralDiagnostics.Structs.NetworkInterface
        ip_addresses: list[str] = []
        for network_interface in node.get_attribute_value(
            0, cluster=None, attribute=attribute
        ):
            # ignore invalid/non-operational interfaces
            if not network_interface.isOperational:
                continue
            # enumerate ipv4 and ipv6 addresses
            for ipv4_address_hex in network_interface.IPv4Addresses:
                ipv4_address = convert_ip_address(ipv4_address_hex)
                ip_addresses.append(ipv4_address)
            for ipv6_address_hex in network_interface.IPv6Addresses:
                ipv6_address = convert_ip_address(ipv6_address_hex, True)
                ip_addresses.append(ipv6_address)
            break
        return ip_addresses

    async def node_diagnostics(self, node_id: int) -> NodeDiagnostics:
        """Gather diagnostics for the given node."""
        # pylint: disable=too-many-statements
        node = self.get_node(node_id)
        ip_addresses = await self.get_node_ip_addresses(node_id)
        # grab some details from the first (operational) network interface
        network_type = NetworkType.UNKNOWN
        mac_address = None
        attribute = Clusters.GeneralDiagnostics.Attributes.NetworkInterfaces
        network_interface: Clusters.GeneralDiagnostics.Structs.NetworkInterface
        for network_interface in (
            node.get_attribute_value(0, cluster=None, attribute=attribute) or []
        ):
            # ignore invalid/non-operational interfaces
            if not network_interface.isOperational:
                continue
            if (
                network_interface.type
                == Clusters.GeneralDiagnostics.Enums.InterfaceTypeEnum.kThread
            ):
                network_type = NetworkType.THREAD
            elif (
                network_interface.type
                == Clusters.GeneralDiagnostics.Enums.InterfaceTypeEnum.kWiFi
            ):
                network_type = NetworkType.WIFI
            elif (
                network_interface.type
                == Clusters.GeneralDiagnostics.Enums.InterfaceTypeEnum.kEthernet
            ):
                network_type = NetworkType.ETHERNET
            else:
                # unknown interface: ignore
                continue
            mac_address = convert_mac_address(network_interface.hardwareAddress)
            break
        else:
            self.logger.warning(
                "Could not determine network_interface info for Node %s, "
                "is it missing the GeneralDiagnostics/NetworkInterfaces Attribute?",
                node_id,
            )
        # get thread/wifi specific info
        node_type = NodeType.UNKNOWN
        network_name = None
        if network_type == NetworkType.THREAD:
            thread_cluster: Clusters.ThreadNetworkDiagnostics = node.get_cluster(
                0, Clusters.ThreadNetworkDiagnostics
            )
            if thread_cluster:
                if isinstance(thread_cluster.networkName, bytes):
                    network_name = thread_cluster.networkName.decode(
                        "utf-8", errors="replace"
                    )
                elif thread_cluster.networkName != NullValue:
                    network_name = thread_cluster.networkName

                # parse routing role to (diagnostics) node type
                RoutingRole = Clusters.ThreadNetworkDiagnostics.Enums.RoutingRoleEnum  # noqa: N806
                if thread_cluster.routingRole == RoutingRole.kSleepyEndDevice:
                    node_type = NodeType.SLEEPY_END_DEVICE
                elif thread_cluster.routingRole in (
                    RoutingRole.kLeader,
                    RoutingRole.kRouter,
                ):
                    node_type = NodeType.ROUTING_END_DEVICE
                elif thread_cluster.routingRole in (
                    RoutingRole.kEndDevice,
                    RoutingRole.kReed,
                ):
                    node_type = NodeType.END_DEVICE
        elif network_type == NetworkType.WIFI:
            node_type = NodeType.END_DEVICE
        # use lastNetworkID from NetworkCommissioning cluster as fallback to get the network name
        # this allows getting the SSID as the wifi diagnostics cluster only has the BSSID
        last_network_id: bytes | str | None
        if not network_name and (
            last_network_id := node.get_attribute_value(
                0,
                cluster=None,
                attribute=Clusters.NetworkCommissioning.Attributes.LastNetworkID,
            )
        ):
            if isinstance(last_network_id, bytes):
                network_name = last_network_id.decode("utf-8", errors="replace")
            elif last_network_id != NullValue:
                network_name = last_network_id
        # last resort to get the (wifi) networkname;
        # enumerate networks on the NetworkCommissioning cluster
        networks: list[Clusters.NetworkCommissioning.Structs.NetworkInfoStruct]
        if not network_name and (
            networks := node.get_attribute_value(
                0,
                cluster=None,
                attribute=Clusters.NetworkCommissioning.Attributes.Networks,
            )
        ):
            for network in networks:
                if not network.connected:
                    continue
                if isinstance(network.networkID, bytes):
                    network_name = network.networkID.decode("utf-8", errors="replace")
                    break
                if network.networkID != NullValue:
                    network_name = network.networkID
                    break
        # override node type if node is a bridge
        if node.node_data.is_bridge:
            node_type = NodeType.BRIDGE
        # get active fabrics for this node
        active_fabrics = await self.get_matter_fabrics(node_id)
        # get active fabric index
        fabric_index = node.get_attribute_value(
            0, None, Clusters.OperationalCredentials.Attributes.CurrentFabricIndex
        )
        return NodeDiagnostics(
            node_id=node_id,
            network_type=network_type,
            node_type=node_type,
            network_name=network_name,
            ip_adresses=ip_addresses,
            mac_address=mac_address,
            available=node.available,
            active_fabrics=active_fabrics,
            active_fabric_index=fabric_index,
        )

    async def send_device_command(
        self,
        node_id: int,
        endpoint_id: int,
        command: ClusterCommand,
        response_type: Any | None = None,
        timed_request_timeout_ms: int | None = None,
        interaction_timeout_ms: int | None = None,
    ) -> Any:
        """Send a command to a Matter node/device."""
        try:
            command_name = command.__class__.__name__
        except AttributeError:
            # handle case where only the class was provided instead of an instance of it.
            command_name = command.__name__
        return await self.send_command(
            APICommand.DEVICE_COMMAND,
            node_id=node_id,
            endpoint_id=endpoint_id,
            cluster_id=command.cluster_id,
            command_name=command_name,
            payload=dataclass_to_dict(command),
            response_type=response_type,
            timed_request_timeout_ms=timed_request_timeout_ms,
            interaction_timeout_ms=interaction_timeout_ms,
        )

    async def read_attribute(
        self,
        node_id: int,
        attribute_path: str | list[str],
    ) -> dict[str, Any]:
        """Read one or more attribute(s) on a node by specifying an attributepath."""
        updated_values = await self.send_command(
            APICommand.READ_ATTRIBUTE,
            require_schema=9,
            node_id=node_id,
            attribute_path=attribute_path,
        )
        return cast(dict[str, Any], updated_values)

    async def refresh_attribute(
        self,
        node_id: int,
        attribute_path: str,
    ) -> None:
        """Read attribute(s) on a node and store the updated value(s)."""
        updated_values = await self.read_attribute(node_id, attribute_path)
        for attr_path, value in updated_values.items():
            self._nodes[node_id].update_attribute(attr_path, value)

    async def write_attribute(
        self,
        node_id: int,
        attribute_path: str,
        value: Any,
    ) -> Any:
        """Write an attribute(value) on a target node."""
        return await self.send_command(
            APICommand.WRITE_ATTRIBUTE,
            require_schema=4,
            node_id=node_id,
            attribute_path=attribute_path,
            value=value,
        )

    async def remove_node(self, node_id: int) -> None:
        """Remove a Matter node/device from the fabric."""
        await self.send_command(APICommand.REMOVE_NODE, node_id=node_id)

    async def interview_node(self, node_id: int) -> None:
        """Interview a node."""
        await self.send_command(APICommand.INTERVIEW_NODE, node_id=node_id)

    async def check_node_update(self, node_id: int) -> MatterSoftwareVersion | None:
        """Check Node for updates.

        Return a dict with the available update information. Most notable
        "softwareVersion" contains the integer value of the update version which then
        can be used for the update_node command to trigger the update.

        The "softwareVersionString" is a human friendly version string.
        """
        data = await self.send_command(
            APICommand.CHECK_NODE_UPDATE, node_id=node_id, require_schema=10
        )
        if data is None:
            return None

        return dataclass_from_dict(MatterSoftwareVersion, data)

    async def update_node(
        self,
        node_id: int,
        software_version: int | str,
    ) -> None:
        """Start node update to a particular version."""
        await self.send_command(
            APICommand.UPDATE_NODE,
            node_id=node_id,
            software_version=software_version,
            require_schema=10,
        )

    def _prepare_message(
        self,
        command: str,
        require_schema: int | None = None,
        **kwargs: Any,
    ) -> CommandMessage:
        if not self.connection.connected:
            raise InvalidState("Not connected")

        if (
            require_schema is not None
            and self.server_info is not None
            and require_schema > self.server_info.schema_version
        ):
            raise ServerVersionTooOld(
                "Command not available due to incompatible server version. Update the Matter "
                f"Server to a version that supports at least api schema {require_schema}.",
            )

        return CommandMessage(
            message_id=uuid.uuid4().hex,
            command=command,
            args=kwargs,
        )

    async def send_command(
        self,
        command: str,
        require_schema: int | None = None,
        **kwargs: Any,
    ) -> Any:
        """Send a command and get a response."""
        if not self._loop:
            raise InvalidState("Not connected")

        message = self._prepare_message(command, require_schema, **kwargs)
        future: asyncio.Future[Any] = self._loop.create_future()
        self._result_futures[message.message_id] = future
        await self.connection.send_message(message)
        try:
            return await future
        finally:
            self._result_futures.pop(message.message_id)

    async def send_command_no_wait(
        self,
        command: str,
        require_schema: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Send a command without waiting for the response."""

        message = self._prepare_message(command, require_schema, **kwargs)
        await self.connection.send_message(message)

    async def get_diagnostics(self) -> ServerDiagnostics:
        """Return a full dump of the server (for diagnostics)."""
        data = await self.send_command(APICommand.SERVER_DIAGNOSTICS)
        return dataclass_from_dict(ServerDiagnostics, data)

    async def connect(self) -> None:
        """Connect to the Matter Server (over Websockets)."""
        self._loop = asyncio.get_running_loop()
        if self.connection.connected:
            # already connected
            return
        # NOTE: connect will raise when connecting failed
        await self.connection.connect()

    async def start_listening(self, init_ready: asyncio.Event | None = None) -> None:
        """Start listening to the websocket (and receive initial state)."""
        await self.connect()

        try:
            message = CommandMessage(
                message_id=uuid.uuid4().hex, command=APICommand.START_LISTENING
            )
            await self.connection.send_message(message)
            nodes_msg = cast(
                SuccessResultMessage, await self.connection.receive_message_or_raise()
            )
            # a full dump of all nodes will be the result of the start_listening command
            # create MatterNode objects from the basic MatterNodeData objects
            nodes = [
                MatterNode(dataclass_from_dict(MatterNodeData, x))
                for x in nodes_msg.result
            ]
            self._nodes = {node.node_id: node for node in nodes}
            # once we've hit this point we're all set
            self.logger.info("Matter client initialized.")
            if init_ready is not None:
                init_ready.set()

            # keep reading incoming messages
            while not self._stop_called:
                msg = await self.connection.receive_message_or_raise()
                self._handle_incoming_message(msg)
        except ConnectionClosed:
            pass
        finally:
            await self.disconnect()

    async def disconnect(self) -> None:
        """Disconnect the client and cleanup."""
        self._stop_called = True
        # cancel all command-tasks awaiting a result
        for future in self._result_futures.values():
            future.cancel()
        await self.connection.disconnect()

    def _handle_incoming_message(self, msg: MessageType) -> None:
        """
        Handle incoming message.

        Run all async tasks in a wrapper to log appropriately.
        """
        # handle result message
        if isinstance(msg, ResultMessageBase):
            future = self._result_futures.get(msg.message_id)

            if future is None:
                # no listener for this result
                return

            if isinstance(msg, SuccessResultMessage):
                future.set_result(msg.result)
                return
            if isinstance(msg, ErrorResultMessage):
                exc = ERROR_MAP[msg.error_code]
                future.set_exception(exc(msg.details))
                return

        # handle EventMessage
        if isinstance(msg, EventMessage):
            self._handle_event_message(msg)
            return

        # Log anything we can't handle here
        self.logger.debug(
            "Received message with unknown type '%s': %s",
            type(msg),
            msg,
        )

    def _handle_event_message(self, msg: EventMessage) -> None:
        """Handle incoming event from the server."""
        if msg.event in (EventType.NODE_ADDED, EventType.NODE_UPDATED):
            # an update event can potentially arrive for a not yet known node
            node_data = dataclass_from_dict(MatterNodeData, msg.data)
            node = self._nodes.get(node_data.node_id)
            if node is None:
                event = EventType.NODE_ADDED
                node = MatterNode(node_data)
                self._nodes[node.node_id] = node
                self.logger.debug("New node added: %s", node.node_id)
            else:
                event = EventType.NODE_UPDATED
                node.update(node_data)
                self.logger.debug("Node updated: %s", node.node_id)
            self._signal_event(event, data=node, node_id=node.node_id)
            return
        if msg.event == EventType.NODE_REMOVED:
            node_id = msg.data
            self.logger.debug("Node removed: %s", node_id)
            self._signal_event(EventType.NODE_REMOVED, data=node_id, node_id=node_id)
            # cleanup node only after signalling subscribers
            self._nodes.pop(node_id, None)
            return
        if msg.event == EventType.ENDPOINT_REMOVED:
            node_id = msg.data["node_id"]
            endpoint_id = msg.data["endpoint_id"]
            self.logger.debug("Endpoint removed: %s/%s", node_id, endpoint_id)
            self._signal_event(
                EventType.ENDPOINT_REMOVED, data=msg.data, node_id=node_id
            )
            # cleanup endpoint only after signalling subscribers
            if node := self._nodes.get(node_id):
                node.endpoints.pop(endpoint_id, None)
            return
        if msg.event == EventType.ATTRIBUTE_UPDATED:
            # data is tuple[node_id, attribute_path, new_value]
            node_id, attribute_path, new_value = msg.data
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(
                    "Attribute updated: Node: %s - Attribute: %s - New value: %s",
                    node_id,
                    attribute_path,
                    new_value,
                )
            self._nodes[node_id].update_attribute(attribute_path, new_value)
            self._signal_event(
                EventType.ATTRIBUTE_UPDATED,
                data=new_value,
                node_id=node_id,
                attribute_path=attribute_path,
            )
            return
        if msg.event == EventType.ENDPOINT_ADDED:
            node_id = msg.data["node_id"]
            endpoint_id = msg.data["endpoint_id"]
            self.logger.debug("Endpoint added: %s/%s", node_id, endpoint_id)
        if msg.event == EventType.NODE_EVENT:
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(
                    "Node event: %s",
                    msg.data,
                )
            node_event = dataclass_from_dict(MatterNodeEvent, msg.data)
            self._signal_event(
                EventType.NODE_EVENT,
                data=node_event,
                node_id=node_event.node_id,
            )
            return
        # simply forward all other events as-is
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("Received event: %s", msg)
        self._signal_event(msg.event, msg.data)

    def _signal_event(
        self,
        event: EventType,
        data: Any = None,
        node_id: Optional[int] = None,
        attribute_path: Optional[str] = None,
    ) -> None:
        """Signal event to all subscribers."""
        # instead of iterating all subscribers we iterate over subscription keys
        # each callback is stored under a specific key based on the filters
        for evt_key in (event.value, SUB_WILDCARD):
            for node_key in (node_id, SUB_WILDCARD):
                if node_key is None:
                    continue
                for attribute_path_key in (attribute_path, SUB_WILDCARD):
                    if attribute_path_key is None:
                        continue
                    key = f"{evt_key}/{node_key}/{attribute_path_key}"
                    for callback in self._subscribers.get(key, []):
                        callback(event, data)

    async def __aenter__(self) -> "MatterClient":
        """Initialize and connect the Matter Websocket client."""
        await self.connect()
        return self

    async def __aexit__(
        self, exc_type: Exception, exc_value: str, traceback: TracebackType
    ) -> None:
        """Disconnect from the websocket."""
        await self.disconnect()

    def __repr__(self) -> str:
        """Return the representation."""
        url = self.connection.ws_server_url
        prefix = "" if self.connection.connected else "not "
        return f"{type(self).__name__}(ws_server_url={url!r}, {prefix}connected)"
