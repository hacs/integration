"""Definitions for custom (vendor specific) Matter clusters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from chip import ChipUtility
from chip.clusters.ClusterObjects import (
    Cluster,
    ClusterAttributeDescriptor,
    ClusterObjectDescriptor,
    ClusterObjectFieldDescriptor,
)
from chip.clusters.Objects import BasicInformation, ElectricalPowerMeasurement
from chip.tlv import float32, uint

from matter_server.common.helpers.util import (
    create_attribute_path_from_attribute,
    parse_attribute_path,
)

if TYPE_CHECKING:
    from matter_server.common.models import MatterNodeData


# pylint: disable=invalid-name,arguments-renamed,no-self-argument
# mypy: ignore_errors=true


ALL_CUSTOM_CLUSTERS: dict[int, Cluster] = {}
ALL_CUSTOM_ATTRIBUTES: dict[int, dict[int, ClusterAttributeDescriptor]] = {}

VENDOR_ID_EVE = 4874


@dataclass
class CustomClusterMixin:
    """Base model for a vendor specific custom cluster."""

    id: ClassVar[int]  # cluster id

    @staticmethod
    def should_poll(node_data: MatterNodeData) -> bool:  # noqa: ARG004
        """Check if the (entire) custom cluster should be polled for state changes."""
        return False

    def __init_subclass__(cls: Cluster, *args, **kwargs) -> None:
        """Register a subclass."""
        super().__init_subclass__(*args, **kwargs)
        ALL_CUSTOM_CLUSTERS[cls.id] = cls


@dataclass
class CustomClusterAttributeMixin:
    """Base model for a vendor specific custom cluster attribute."""

    @staticmethod
    def should_poll(node_data: MatterNodeData) -> bool:  # noqa: ARG004
        """Check if the custom attribute should be polled for state changes."""
        return False

    def __init_subclass__(cls: ClusterAttributeDescriptor, *args, **kwargs) -> None:
        """Register a subclass."""
        super().__init_subclass__(*args, **kwargs)
        if cls.cluster_id not in ALL_CUSTOM_ATTRIBUTES:
            ALL_CUSTOM_ATTRIBUTES[cls.cluster_id] = {}
        ALL_CUSTOM_ATTRIBUTES[cls.cluster_id][cls.attribute_id] = cls


def should_poll_eve_energy(node_data: MatterNodeData) -> bool:
    """Check if the (Eve Energy) custom attribute should be polled for state changes."""
    attr_path = create_attribute_path_from_attribute(
        0, BasicInformation.Attributes.VendorID
    )
    if node_data.attributes.get(attr_path) != VENDOR_ID_EVE:
        # Some implementation (such as MatterBridge) use the
        # Eve cluster to send the power measurements. Filter that out.
        return False
    # if the ElectricalPowerMeasurement cluster is NOT present,
    # we should poll the custom Eve cluster attribute(s).
    attr_path = create_attribute_path_from_attribute(
        2, ElectricalPowerMeasurement.Attributes.AttributeList
    )
    return node_data.attributes.get(attr_path) is None


@dataclass
class EveCluster(Cluster, CustomClusterMixin):
    """Custom (vendor-specific) cluster for Eve - Vendor ID 4874 (0x130a)."""

    id: ClassVar[int] = 0x130AFC01

    @ChipUtility.classproperty
    def descriptor(cls) -> ClusterObjectDescriptor:
        """Return descriptor for this cluster."""
        return ClusterObjectDescriptor(
            Fields=[
                ClusterObjectFieldDescriptor(
                    Label="timesOpened", Tag=0x130A0006, Type=int
                ),
                ClusterObjectFieldDescriptor(
                    Label="watt", Tag=0x130A000A, Type=float32
                ),
                ClusterObjectFieldDescriptor(
                    Label="wattAccumulated", Tag=0x130A000B, Type=float32
                ),
                ClusterObjectFieldDescriptor(
                    Label="wattAccumulatedControlPoint", Tag=0x130A000E, Type=float32
                ),
                ClusterObjectFieldDescriptor(
                    Label="voltage", Tag=0x130A0008, Type=float32
                ),
                ClusterObjectFieldDescriptor(
                    Label="current", Tag=0x130A0009, Type=float32
                ),
                ClusterObjectFieldDescriptor(
                    Label="altitude", Tag=0x130A0013, Type=float32
                ),
                ClusterObjectFieldDescriptor(
                    Label="pressure", Tag=0x130A0014, Type=float32
                ),
                ClusterObjectFieldDescriptor(
                    Label="valvePosition", Tag=0x130A0018, Type=int
                ),
                ClusterObjectFieldDescriptor(
                    Label="motionSensitivity", Tag=0x130A000D, Type=int
                ),
            ]
        )

    timesOpened: int | None = None
    watt: float32 | None = None
    wattAccumulated: float32 | None = None
    wattAccumulatedControlPoint: float32 | None = None
    voltage: float32 | None = None
    current: float32 | None = None
    altitude: float32 | None = None
    pressure: float32 | None = None
    valvePosition: int | None = None
    motionSensitivity: int | None = None

    class Attributes:
        """Attributes for the Eve Cluster."""

        @dataclass
        class TimesOpened(ClusterAttributeDescriptor, CustomClusterAttributeMixin):
            """TimesOpened Attribute within the Eve Cluster."""

            @ChipUtility.classproperty
            def cluster_id(cls) -> int:
                """Return cluster id."""
                return 0x130AFC01

            @ChipUtility.classproperty
            def attribute_id(cls) -> int:
                """Return attribute id."""
                return 0x130A0006

            @ChipUtility.classproperty
            def attribute_type(cls) -> ClusterObjectFieldDescriptor:
                """Return attribute type."""
                return ClusterObjectFieldDescriptor(Type=int)

            value: int = 0

        @dataclass
        class Watt(ClusterAttributeDescriptor, CustomClusterAttributeMixin):
            """Watt Attribute within the Eve Cluster."""

            should_poll = should_poll_eve_energy

            @ChipUtility.classproperty
            def cluster_id(cls) -> int:
                """Return cluster id."""
                return 0x130AFC01

            @ChipUtility.classproperty
            def attribute_id(cls) -> int:
                """Return attribute id."""
                return 0x130A000A

            @ChipUtility.classproperty
            def attribute_type(cls) -> ClusterObjectFieldDescriptor:
                """Return attribute type."""
                return ClusterObjectFieldDescriptor(Type=float32)

            value: float32 = 0

        @dataclass
        class WattAccumulated(ClusterAttributeDescriptor, CustomClusterAttributeMixin):
            """WattAccumulated Attribute within the Eve Cluster."""

            should_poll = should_poll_eve_energy

            @ChipUtility.classproperty
            def cluster_id(cls) -> int:
                """Return cluster id."""
                return 0x130AFC01

            @ChipUtility.classproperty
            def attribute_id(cls) -> int:
                """Return attribute id."""
                return 0x130A000B

            @ChipUtility.classproperty
            def attribute_type(cls) -> ClusterObjectFieldDescriptor:
                """Return attribute type."""
                return ClusterObjectFieldDescriptor(Type=float32)

            value: float32 = 0

        @dataclass
        class WattAccumulatedControlPoint(
            ClusterAttributeDescriptor, CustomClusterAttributeMixin
        ):
            """wattAccumulatedControlPoint Attribute within the Eve Cluster."""

            should_poll = should_poll_eve_energy

            @ChipUtility.classproperty
            def cluster_id(cls) -> int:
                """Return cluster id."""
                return 0x130AFC01

            @ChipUtility.classproperty
            def attribute_id(cls) -> int:
                """Return attribute id."""
                return 0x130A000E

            @ChipUtility.classproperty
            def attribute_type(cls) -> ClusterObjectFieldDescriptor:
                """Return attribute type."""
                return ClusterObjectFieldDescriptor(Type=float32)

            value: float32 = 0

        @dataclass
        class Voltage(ClusterAttributeDescriptor, CustomClusterAttributeMixin):
            """Voltage Attribute within the Eve Cluster."""

            should_poll = should_poll_eve_energy

            @ChipUtility.classproperty
            def cluster_id(cls) -> int:
                """Return cluster id."""
                return 0x130AFC01

            @ChipUtility.classproperty
            def attribute_id(cls) -> int:
                """Return attribute id."""
                return 0x130A0008

            @ChipUtility.classproperty
            def attribute_type(cls) -> ClusterObjectFieldDescriptor:
                """Return attribute type."""
                return ClusterObjectFieldDescriptor(Type=float32)

            value: float32 = 0

        @dataclass
        class Current(ClusterAttributeDescriptor, CustomClusterAttributeMixin):
            """Current Attribute within the Eve Cluster."""

            should_poll = should_poll_eve_energy

            @ChipUtility.classproperty
            def cluster_id(cls) -> int:
                """Return cluster id."""
                return 0x130AFC01

            @ChipUtility.classproperty
            def attribute_id(cls) -> int:
                """Return attribute id."""
                return 0x130A0009

            @ChipUtility.classproperty
            def attribute_type(cls) -> ClusterObjectFieldDescriptor:
                """Return attribute type."""
                return ClusterObjectFieldDescriptor(Type=float32)

            value: float32 = 0

        @dataclass
        class Altitude(ClusterAttributeDescriptor, CustomClusterAttributeMixin):
            """Altitude Attribute within the Eve Cluster."""

            @ChipUtility.classproperty
            def cluster_id(cls) -> int:
                """Return cluster id."""
                return 0x130AFC01

            @ChipUtility.classproperty
            def attribute_id(cls) -> int:
                """Return attribute id."""
                return 0x130A0013

            @ChipUtility.classproperty
            def attribute_type(cls) -> ClusterObjectFieldDescriptor:
                """Return attribute type."""
                return ClusterObjectFieldDescriptor(Type=float32)

            value: float32 = 0

        @dataclass
        class Pressure(ClusterAttributeDescriptor, CustomClusterAttributeMixin):
            """Pressure Attribute within the Eve Cluster."""

            @ChipUtility.classproperty
            def cluster_id(cls) -> int:
                """Return cluster id."""
                return 0x130AFC01

            @ChipUtility.classproperty
            def attribute_id(cls) -> int:
                """Return attribute id."""
                return 0x130A0014

            @ChipUtility.classproperty
            def attribute_type(cls) -> ClusterObjectFieldDescriptor:
                """Return attribute type."""
                return ClusterObjectFieldDescriptor(Type=float32)

            value: float32 = 0

        @dataclass
        class ValvePosition(ClusterAttributeDescriptor, CustomClusterAttributeMixin):
            """ValvePosition Attribute within the Eve Cluster."""

            @ChipUtility.classproperty
            def cluster_id(cls) -> int:
                """Return cluster id."""
                return 0x130AFC01

            @ChipUtility.classproperty
            def attribute_id(cls) -> int:
                """Return attribute id."""
                return 0x130A0018

            @ChipUtility.classproperty
            def attribute_type(cls) -> ClusterObjectFieldDescriptor:
                """Return attribute type."""
                return ClusterObjectFieldDescriptor(Type=int)

            value: int = 0

        @dataclass
        class MotionSensitivity(
            ClusterAttributeDescriptor, CustomClusterAttributeMixin
        ):
            """MotionSensitivity Attribute within the Eve Cluster."""

            @ChipUtility.classproperty
            def cluster_id(cls) -> int:
                """Return cluster id."""
                return 0x130AFC01

            @ChipUtility.classproperty
            def attribute_id(cls) -> int:
                """Return attribute id."""
                return 0x130A000D

            @ChipUtility.classproperty
            def attribute_type(cls) -> ClusterObjectFieldDescriptor:
                """Return attribute type."""
                return ClusterObjectFieldDescriptor(Type=int)

            value: int = 0


@dataclass
class NeoCluster(Cluster, CustomClusterMixin):
    """Custom (vendor-specific) cluster for Neo - Vendor ID 4991 (0x137F)."""

    id: ClassVar[int] = 0x00125DFC11

    @ChipUtility.classproperty
    def descriptor(cls) -> ClusterObjectDescriptor:
        """Return descriptor for this cluster."""
        return ClusterObjectDescriptor(
            Fields=[
                ClusterObjectFieldDescriptor(
                    Label="wattAccumulated", Tag=0x00125D0021, Type=float32
                ),
                ClusterObjectFieldDescriptor(
                    Label="watt", Tag=0x00125D0023, Type=float32
                ),
                ClusterObjectFieldDescriptor(
                    Label="current", Tag=0x00125D0022, Type=float32
                ),
                ClusterObjectFieldDescriptor(
                    Label="voltage", Tag=0x00125D0024, Type=float32
                ),
            ]
        )

    watt: float32 | None = None
    wattAccumulated: float32 | None = None
    voltage: float32 | None = None
    current: float32 | None = None

    class Attributes:
        """Attributes for the Neo Cluster."""

        @dataclass
        class Watt(ClusterAttributeDescriptor, CustomClusterAttributeMixin):
            """Watt Attribute within the Neo Cluster."""

            @ChipUtility.classproperty
            def cluster_id(cls) -> int:
                """Return cluster id."""
                return 0x00125DFC11

            @ChipUtility.classproperty
            def attribute_id(cls) -> int:
                """Return attribute id."""
                return 0x00125D0023

            @ChipUtility.classproperty
            def attribute_type(cls) -> ClusterObjectFieldDescriptor:
                """Return attribute type."""
                return ClusterObjectFieldDescriptor(Type=float32)

            value: float32 = 0

        @dataclass
        class WattAccumulated(ClusterAttributeDescriptor, CustomClusterAttributeMixin):
            """WattAccumulated Attribute within the Neo Cluster."""

            @ChipUtility.classproperty
            def cluster_id(cls) -> int:
                """Return cluster id."""
                return 0x00125DFC11

            @ChipUtility.classproperty
            def attribute_id(cls) -> int:
                """Return attribute id."""
                return 0x00125D0021

            @ChipUtility.classproperty
            def attribute_type(cls) -> ClusterObjectFieldDescriptor:
                """Return attribute type."""
                return ClusterObjectFieldDescriptor(Type=float32)

            value: float32 = 0

        @dataclass
        class Voltage(ClusterAttributeDescriptor, CustomClusterAttributeMixin):
            """Voltage Attribute within the Neo Cluster."""

            @ChipUtility.classproperty
            def cluster_id(cls) -> int:
                """Return cluster id."""
                return 0x00125DFC11

            @ChipUtility.classproperty
            def attribute_id(cls) -> int:
                """Return attribute id."""
                return 0x00125D0024

            @ChipUtility.classproperty
            def attribute_type(cls) -> ClusterObjectFieldDescriptor:
                """Return attribute type."""
                return ClusterObjectFieldDescriptor(Type=float32)

            value: float32 = 0

        @dataclass
        class Current(ClusterAttributeDescriptor, CustomClusterAttributeMixin):
            """Current Attribute within the Neo Cluster."""

            @ChipUtility.classproperty
            def cluster_id(cls) -> int:
                """Return cluster id."""
                return 0x00125DFC11

            @ChipUtility.classproperty
            def attribute_id(cls) -> int:
                """Return attribute id."""
                return 0x00125D0022

            @ChipUtility.classproperty
            def attribute_type(cls) -> ClusterObjectFieldDescriptor:
                """Return attribute type."""
                return ClusterObjectFieldDescriptor(Type=float32)

            value: float32 = 0


@dataclass
class ThirdRealityMeteringCluster(Cluster, CustomClusterMixin):
    """Custom (vendor-specific) PowerMetering cluster for ThirdReality."""

    id: ClassVar[int] = 0x130DFC02

    @ChipUtility.classproperty
    def descriptor(cls) -> ClusterObjectDescriptor:
        """Return descriptor for this cluster."""
        return ClusterObjectDescriptor(
            Fields=[
                ClusterObjectFieldDescriptor(
                    Label="currentSummationDelivered", Tag=0x0000, Type=uint
                ),
                ClusterObjectFieldDescriptor(
                    Label="instantaneousDemand", Tag=0x0400, Type=uint
                ),
            ]
        )

    currentSummationDelivered: uint | None = None
    instantaneousDemand: uint | None = None

    class Attributes:
        """Attributes for the custom Cluster."""

        @dataclass
        class CurrentSummationDelivered(
            ClusterAttributeDescriptor, CustomClusterAttributeMixin
        ):
            """CurrentSummationDelivered represents the most recent summed value of Energy consumed in the premise.

            CurrentSummationDelivered is updated continuously as new measurements are made.
            This attribute is Read only.
            Value is set to zero when leave command is received (beginning version 2.6.15),
            or local factory reset(10s) is performed on the device..
            """

            @ChipUtility.classproperty
            def cluster_id(cls) -> int:
                """Return cluster id."""
                return 0x130DFC02

            @ChipUtility.classproperty
            def attribute_id(cls) -> int:
                """Return attribute id."""
                return 0x0000

            @ChipUtility.classproperty
            def attribute_type(cls) -> ClusterObjectFieldDescriptor:
                """Return attribute type."""
                return ClusterObjectFieldDescriptor(Type=uint)

            value: uint = 0

        @dataclass
        class InstantaneousDemand(
            ClusterAttributeDescriptor, CustomClusterAttributeMixin
        ):
            """
            InstantaneousDemand represents the current Demand of Energy delivered at the premise.

            Device is able measure only positive values indicate Demand delivered to the premise.
            InstantaneousDemand is updated continuously as new measurements are made.
            The frequency of updates to this field is specific to the metering device,
            but should be within the range of once every second to once every 5 seconds.
            The same multiplier and divisor values used for Current Summation Delivered (Energy) will be used.
            If connected load is below 1W, this attribute is set to 0 and no accumulation of energy is done.
            """

            @ChipUtility.classproperty
            def cluster_id(cls) -> int:
                """Return cluster id."""
                return 0x130DFC02

            @ChipUtility.classproperty
            def attribute_id(cls) -> int:
                """Return attribute id."""
                return 0x0400

            @ChipUtility.classproperty
            def attribute_type(cls) -> ClusterObjectFieldDescriptor:
                """Return attribute type."""
                return ClusterObjectFieldDescriptor(Type=uint)

            value: uint = 0


def check_polled_attributes(node_data: MatterNodeData) -> set[str]:
    """Check if custom attributes are present in the node data that need to be polled."""
    attributes_to_poll: set[str] = set()
    for attr_path in node_data.attributes:
        endpoint_id, cluster_id, attribute_id = parse_attribute_path(attr_path)
        if not (custom_cluster := ALL_CUSTOM_CLUSTERS.get(cluster_id)):
            continue
        if custom_cluster.should_poll(node_data):
            # the entire cluster needs to be polled
            attributes_to_poll.add(f"{endpoint_id}/{cluster_id}/*")
            continue
        custom_attribute = ALL_CUSTOM_ATTRIBUTES[cluster_id].get(attribute_id)
        if custom_attribute and custom_attribute.should_poll(node_data):
            # this attribute needs to be polled
            attributes_to_poll.add(attr_path)
    return attributes_to_poll
