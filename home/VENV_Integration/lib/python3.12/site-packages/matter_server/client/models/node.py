"""Matter node."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging
from typing import TYPE_CHECKING, Any, TypeVar, cast

from chip.clusters import Objects as Clusters
from chip.clusters.ClusterObjects import ALL_ATTRIBUTES, ALL_CLUSTERS

from matter_server.common.helpers.util import (
    create_attribute_path,
    parse_attribute_path,
    parse_value,
)

from .device_types import (
    ALL_TYPES as DEVICE_TYPES,
    Aggregator,
    BridgedDevice,
    DeviceType,
    RootNode,
)

if TYPE_CHECKING:
    from matter_server.common.models import MatterNodeData

LOGGER = logging.getLogger(__name__)

# pylint: disable=invalid-name
_CLUSTER_T = TypeVar("_CLUSTER_T", bound=Clusters.Cluster)
_ATTRIBUTE_T = TypeVar("_ATTRIBUTE_T", bound=Clusters.ClusterAttributeDescriptor)
# pylint: enable=invalid-name


def get_object_params(
    descriptor: Clusters.ClusterObjectDescriptor, object_id: int
) -> tuple[str, type]:
    """Parse label/key and type for an object from the descriptors, given the raw object id."""
    for desc in descriptor.Fields:
        if desc.Tag == object_id:
            return (desc.Label, desc.Type)
    raise KeyError(f"No descriptor found for object {object_id}")


@dataclass
class MatterFabricData:
    """Data about a Matter fabric."""

    fabric_id: int
    vendor_id: int
    fabric_index: int
    fabric_label: str | None = None
    vendor_name: str | None = None


class MatterEndpoint:
    """Representation of a Matter Endpoint."""

    def __init__(
        self,
        endpoint_id: int,
        attributes_data: dict[str, Any],
        node: MatterNode,
    ) -> None:
        """Initialize MatterEndpoint."""
        self.node = node
        self.endpoint_id = endpoint_id
        self.clusters: dict[int, Clusters.Cluster] = {}
        self.device_types: set[type[DeviceType]] = set()
        self.update(attributes_data)

    @property
    def is_bridged_device(self) -> bool:
        """Return if this endpoint represents a Bridged device."""
        return BridgedDevice in self.device_types

    @property
    def is_composed_device(self) -> bool:
        """Return if this endpoint belons to a composed device."""
        return self.node.get_compose_parent(self.endpoint_id) is not None

    @property
    def device_info(
        self,
    ) -> Clusters.BasicInformation | Clusters.BridgedDeviceBasicInformation:
        """
        Return device info.

        If this endpoint represents a BridgedDevice, returns BridgedDeviceBasic.
        If this endpoint represents a ComposedDevice, returns the info of the compose device.
        Otherwise, returns BasicInformation from the Node itself (endpoint 0).
        """
        if self.is_bridged_device:
            return self.get_cluster(Clusters.BridgedDeviceBasicInformation)
        if compose_parent := self.node.get_compose_parent(self.endpoint_id):
            return compose_parent.device_info
        return self.node.device_info

    def has_cluster(self, cluster: type[_CLUSTER_T] | int) -> bool:
        """
        Check if endpoint has a specific cluster.

        Provide the cluster to lookup either as the class/type or the id.
        """
        if isinstance(cluster, type):
            return cluster.id in self.clusters
        return cluster in self.clusters

    def get_cluster(self, cluster: type[_CLUSTER_T] | int) -> _CLUSTER_T | None:
        """
        Get a full Cluster object containing all attributes.

        Provide the cluster to lookup either as the class/type or the id.
        Return None if the Cluster is not present on the node.
        """
        if isinstance(cluster, type):
            return self.clusters.get(cluster.id)
        return self.clusters.get(cluster)

    def get_attribute_value(
        self,
        cluster: type[_CLUSTER_T] | int | None,
        attribute: int | type[_ATTRIBUTE_T],
    ) -> Any:
        """
        Return Matter Cluster Attribute object for given parameters.

        Either supply a cluster id and attribute id or omit cluster
        and supply the Attribute class/type.
        """
        if cluster is None:
            # allow sending None for Cluster to auto resolve it from the Attribute
            if isinstance(attribute, int):
                raise TypeError("Attribute can not be integer if Cluster is omitted")
            cluster = attribute.cluster_id
        # get cluster first, grab value from cluster instance next
        if cluster_obj := self.get_cluster(cluster):
            if isinstance(attribute, type):
                attribute_name, _ = get_object_params(
                    cluster_obj.descriptor, attribute.attribute_id
                )
                return getattr(cluster_obj, attribute_name)
            # actual value is just a class attribute on the cluster instance
            # NOTE: do not use the value on the ClusterAttribute
            # instance itself as that is not used!
            attribute_name, _ = get_object_params(cluster_obj.descriptor, attribute)
            return getattr(
                cluster_obj,
                attribute_name,
            )
        return None

    def has_attribute(
        self,
        cluster: type[_CLUSTER_T] | int | None,
        attribute: int | type[_ATTRIBUTE_T],
    ) -> bool:
        """
        Perform a quick check if the endpoint has a specific attribute.

        Either supply a cluster id and attribute id or omit cluster
        and supply the Attribute class/type.
        """
        if cluster is None:
            if isinstance(attribute, int):
                raise TypeError("Attribute can not be integer if Cluster is omitted")
            # allow sending None for Cluster to auto resolve it from the Attribute
            cluster = attribute.cluster_id
        cluster_id = cluster if isinstance(cluster, int) else cluster.id
        attribute_id = (
            attribute if isinstance(attribute, int) else attribute.attribute_id
        )
        # the fastest way to check this is just by checking the AttributePath in the raw data...
        attr_path = create_attribute_path(self.endpoint_id, cluster_id, attribute_id)
        return attr_path in self.node.node_data.attributes

    def set_attribute_value(self, attribute_path: str, attribute_value: Any) -> None:
        """
        Set the value of a Cluster Attribute.

        May only be called by logic that received data from the server.
        Do not modify the data directly from a consumer.
        """
        _, cluster_id, attribute_id = parse_attribute_path(attribute_path)
        if (
            cluster_id not in ALL_CLUSTERS
            or cluster_id not in ALL_ATTRIBUTES
            or attribute_id not in ALL_ATTRIBUTES[cluster_id]
        ):
            # guard for unknown/custom clusters/attributes
            return
        assert cluster_id is not None  # for mypy
        assert attribute_id is not None  # for mypy
        cluster_class: type[Clusters.Cluster] = ALL_CLUSTERS[cluster_id]
        if cluster_id in self.clusters:
            cluster_instance = self.clusters[cluster_id]
        else:
            cluster_instance = cluster_class()
            self.clusters[cluster_id] = cluster_instance

        # unpack cluster attribute, using the descriptor
        attribute_class: type[Clusters.ClusterAttributeDescriptor] = ALL_ATTRIBUTES[
            cluster_id
        ][attribute_id]
        attribute_name, attribute_type = get_object_params(
            cluster_class.descriptor, attribute_id
        )

        # we only set the value at cluster instance level and we leave
        # the underlying Attributes classproperty alone
        attribute_value = parse_value(
            attribute_name, attribute_value, attribute_type, attribute_class().value
        )
        setattr(cluster_instance, attribute_name, attribute_value)

    def update(self, attributes_data: dict[str, Any]) -> None:
        """Update MatterEndpoint from (endpoint-specific) raw Attributes data."""
        # unwrap cluster and clusterattributes from raw node data attributes
        for attribute_path, attribute_value in attributes_data.items():
            self.set_attribute_value(attribute_path, attribute_value)
        # extract device types from Descriptor Cluster
        if cluster := self.get_cluster(Clusters.Descriptor):
            for dev_info in cluster.deviceTypeList:  # type: ignore[unreachable]
                device_type = DEVICE_TYPES.get(dev_info.deviceType)
                if device_type is None:
                    LOGGER.debug("Found unknown device type %s", dev_info)
                    continue
                self.device_types.add(device_type)

    def __repr__(self) -> str:
        """Return the representation."""
        return f"<MatterEndpoint {self.endpoint_id} (node {self.node.node_id})>"


class MatterNode:
    """Representation of a Matter Node."""

    def __init__(self, node_data: MatterNodeData) -> None:
        """Initialize MatterNode from MatterNodeData."""
        self.endpoints: dict[int, MatterEndpoint] = {}
        # composed devices reference to other endpoints through the partsList attribute
        # create a mapping table
        self._composed_endpoints: dict[int, int] = {}
        self.update(node_data)

    @property
    def node_id(self) -> int:
        """Return Node ID."""
        return self.node_data.node_id

    @property
    def name(self) -> str | None:
        """Return friendly name for this node."""
        if info := self.device_info:
            return cast(str, info.nodeLabel)
        return None

    @property
    def available(self) -> bool:
        """Return availability of the node."""
        return self.node_data.available

    @property
    def device_info(self) -> Clusters.BasicInformation:
        """
        Return device info for this Node.

        Returns BasicInformation from the Node itself (endpoint 0).
        """
        return self.get_cluster(0, Clusters.BasicInformation)

    @property
    def is_bridge_device(self) -> bool:
        """Return if this Node is a Bridge/Aggregator device."""
        return self.node_data.is_bridge

    def get_attribute_value(
        self,
        endpoint: int,
        cluster: type[_CLUSTER_T] | int | None,
        attribute: int | type[_ATTRIBUTE_T],
    ) -> Any:
        """Return Matter Cluster Attribute value for given parameters."""
        return self.endpoints[endpoint].get_attribute_value(cluster, attribute)

    def has_cluster(
        self, cluster: type[_CLUSTER_T] | int, endpoint: int | None = None
    ) -> bool:
        """Check if node has a specific cluster on any of the endpoints."""
        return any(
            x
            for x in self.endpoints.values()
            if x.has_cluster(cluster)
            and (endpoint is None or x.endpoint_id == endpoint)
        )

    def get_cluster(
        self, endpoint: int, cluster: type[_CLUSTER_T] | int
    ) -> _CLUSTER_T | None:
        """
        Get a Cluster object containing all attributes.

        Returns None is the Cluster is not present on the node.
        """
        return self.endpoints[endpoint].get_cluster(cluster)

    def get_compose_parent(self, endpoint_id: int) -> MatterEndpoint | None:
        """Return endpoint of parent if the endpoint belongs to a Composed device."""
        if parent_id := self._composed_endpoints.get(endpoint_id):
            return self.endpoints[parent_id]
        return None

    def get_compose_child_ids(self, endpoint_id: int) -> tuple[int, ...] | None:
        """Return endpoint IDs of any child if the endpoint represents a Composed device."""
        return tuple(x for x, y in self._composed_endpoints.items() if y == endpoint_id)

    def update(self, node_data: MatterNodeData) -> None:
        """Update MatterNode from MatterNodeData."""
        self.node_data = node_data
        # collect per endpoint data
        endpoint_data: dict[int, dict[str, Any]] = {}
        for attribute_path, attribute_data in node_data.attributes.items():
            endpoint_id = int(attribute_path.split("/")[0])
            if endpoint_id not in endpoint_data:
                endpoint_data[endpoint_id] = {}
            endpoint_data[endpoint_id][attribute_path] = attribute_data
        for endpoint_id, attributes_data in endpoint_data.items():
            if endpoint_id in self.endpoints:
                self.endpoints[endpoint_id].update(attributes_data)
            else:
                self.endpoints[endpoint_id] = MatterEndpoint(
                    endpoint_id=endpoint_id, attributes_data=attributes_data, node=self
                )
        # composed devices reference to other endpoints through the partsList attribute
        # create a mapping table to quickly map this
        for endpoint in self.endpoints.values():
            if RootNode in endpoint.device_types:
                # ignore root endpoint
                continue
            if Aggregator in endpoint.device_types:
                # ignore Bridge endpoint
                # (as that will also use partsList to indicate its child's)
                continue
            descriptor = endpoint.get_cluster(Clusters.Descriptor)
            if descriptor is None:
                LOGGER.warning(
                    "Found endpoint without a Descriptor: Node %s, endpoint %s",
                    self.node_id,
                    endpoint.endpoint_id,
                )
                continue
            if descriptor.partsList:  # type: ignore[unreachable]
                for endpoint_id in descriptor.partsList:
                    self._composed_endpoints[endpoint_id] = endpoint.endpoint_id

    def update_attribute(self, attribute_path: str, new_value: Any) -> None:
        """Handle Attribute value update."""
        endpoint_id = int(attribute_path.split("/")[0])
        if endpoint_id not in self.endpoints:
            # race condition when a bridge is in the process of adding a new endpoint
            return
        self.endpoints[endpoint_id].set_attribute_value(attribute_path, new_value)

    def __repr__(self) -> str:
        """Return the representation."""
        return f"<MatterNode {self.node_id}>"


class NodeType(Enum):
    """Custom Enum with Matter node types, used for diagnostics."""

    END_DEVICE = "end_device"
    SLEEPY_END_DEVICE = "sleepy_end_device"
    ROUTING_END_DEVICE = "routing_end_device"
    BRIDGE = "bridge"
    UNKNOWN = "unknown"


class NetworkType(Enum):
    """Custom Enum with Matter network types used for diagnostics.."""

    THREAD = "thread"
    WIFI = "wifi"
    ETHERNET = "ethernet"
    UNKNOWN = "unknown"


@dataclass
class NodeDiagnostics:
    """
    Representation of a Node diagnostics message.

    This a custom model intended to be (easily) consumed by Home Assistant
    and constructed from various cluster attribute values.
    """

    node_id: int
    network_type: NetworkType
    node_type: NodeType
    network_name: str | None  # WiFi SSID or Thread network name
    ip_adresses: list[str]
    mac_address: str | None
    available: bool
    active_fabrics: list[MatterFabricData]
    active_fabric_index: int
