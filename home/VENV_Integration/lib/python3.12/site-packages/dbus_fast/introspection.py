import xml.etree.ElementTree as ET
from typing import List, Optional, Union

from .constants import ArgDirection, PropertyAccess
from .errors import InvalidIntrospectionError
from .signature import SignatureType, get_signature_tree
from .validators import assert_interface_name_valid, assert_member_name_valid

# https://dbus.freedesktop.org/doc/dbus-specification.html#introspection-format
# TODO annotations


class Arg:
    """A class that represents an input or output argument to a signal or a method.

    :ivar name: The name of this arg.
    :vartype name: str
    :ivar direction: Whether this is an input or an output argument.
    :vartype direction: :class:`ArgDirection <dbus_fast.ArgDirection>`
    :ivar type: The parsed signature type of this argument.
    :vartype type: :class:`SignatureType <dbus_fast.SignatureType>`
    :ivar signature: The signature string of this argument.
    :vartype signature: str

    :raises:
        - :class:`InvalidMemberNameError <dbus_fast.InvalidMemberNameError>` - If the name of the arg is not valid.
        - :class:`InvalidSignatureError <dbus_fast.InvalidSignatureError>` - If the signature is not valid.
        - :class:`InvalidIntrospectionError <dbus_fast.InvalidIntrospectionError>` - If the signature is not a single complete type.
    """

    def __init__(
        self,
        signature: Union[SignatureType, str],
        direction: Optional[List[ArgDirection]] = None,
        name: Optional[str] = None,
    ):
        if name is not None:
            assert_member_name_valid(name)

        type_ = None
        if type(signature) is SignatureType:
            type_ = signature
            signature = signature.signature
        else:
            tree = get_signature_tree(signature)
            if len(tree.types) != 1:
                raise InvalidIntrospectionError(
                    f"an argument must have a single complete type. (has {len(tree.types)} types)"
                )
            type_ = tree.types[0]

        self.type = type_
        self.signature = signature
        self.name = name
        self.direction = direction

    def from_xml(element: ET.Element, direction: ArgDirection) -> "Arg":
        """Convert a :class:`xml.etree.ElementTree.Element` into a
        :class:`Arg`.

        The element must be valid DBus introspection XML for an ``arg``.

        :param element: The parsed XML element.
        :type element: :class:`xml.etree.ElementTree.Element`
        :param direction: The direction of this arg. Must be specified because it can default to different values depending on if it's in a method or signal.
        :type direction: :class:`ArgDirection <dbus_fast.ArgDirection>`

        :raises:
            - :class:`InvalidIntrospectionError <dbus_fast.InvalidIntrospectionError>` - If the XML tree is not valid introspection data.
        """
        name = element.attrib.get("name")
        signature = element.attrib.get("type")

        if not signature:
            raise InvalidIntrospectionError(
                'a method argument must have a "type" attribute'
            )

        return Arg(signature, direction, name)

    def to_xml(self) -> ET.Element:
        """Convert this :class:`Arg` into an :class:`xml.etree.ElementTree.Element`."""
        element = ET.Element("arg")
        if self.name:
            element.set("name", self.name)

        if self.direction:
            element.set("direction", self.direction.value)
        element.set("type", self.signature)

        return element


class Signal:
    """A class that represents a signal exposed on an interface.

    :ivar name: The name of this signal
    :vartype name: str
    :ivar args: A list of output arguments for this signal.
    :vartype args: list(Arg)
    :ivar signature: The collected signature of the output arguments.
    :vartype signature: str

    :raises:
        - :class:`InvalidMemberNameError <dbus_fast.InvalidMemberNameError>` - If the name of the signal is not a valid member name.
    """

    def __init__(self, name: Optional[str], args: Optional[List[Arg]] = None):
        if name is not None:
            assert_member_name_valid(name)

        self.name = name
        self.args = args or []
        self.signature = "".join(arg.signature for arg in self.args)

    def from_xml(element):
        """Convert an :class:`xml.etree.ElementTree.Element` to a :class:`Signal`.

        The element must be valid DBus introspection XML for a ``signal``.

        :param element: The parsed XML element.
        :type element: :class:`xml.etree.ElementTree.Element`
        :param is_root: Whether this is the root node
        :type is_root: bool

        :raises:
            - :class:`InvalidIntrospectionError <dbus_fast.InvalidIntrospectionError>` - If the XML tree is not valid introspection data.
        """
        name = element.attrib.get("name")
        if not name:
            raise InvalidIntrospectionError('signals must have a "name" attribute')

        args = []
        for child in element:
            if child.tag == "arg":
                args.append(Arg.from_xml(child, ArgDirection.OUT))

        signal = Signal(name, args)

        return signal

    def to_xml(self) -> ET.Element:
        """Convert this :class:`Signal` into an :class:`xml.etree.ElementTree.Element`."""
        element = ET.Element("signal")
        element.set("name", self.name)

        for arg in self.args:
            element.append(arg.to_xml())

        return element


class Method:
    """A class that represents a method exposed on an :class:`Interface`.

    :ivar name: The name of this method.
    :vartype name: str
    :ivar in_args: A list of input arguments to this method.
    :vartype in_args: list(Arg)
    :ivar out_args: A list of output arguments to this method.
    :vartype out_args: list(Arg)
    :ivar in_signature: The collected signature string of the input arguments.
    :vartype in_signature: str
    :ivar out_signature: The collected signature string of the output arguments.
    :vartype out_signature: str

    :raises:
        - :class:`InvalidMemberNameError <dbus_fast.InvalidMemberNameError>` - If the name of this method is not valid.
    """

    def __init__(self, name: str, in_args: List[Arg] = [], out_args: List[Arg] = []):
        assert_member_name_valid(name)

        self.name = name
        self.in_args = in_args
        self.out_args = out_args
        self.in_signature = "".join(arg.signature for arg in in_args)
        self.out_signature = "".join(arg.signature for arg in out_args)

    def from_xml(element: ET.Element) -> "Method":
        """Convert an :class:`xml.etree.ElementTree.Element` to a :class:`Method`.

        The element must be valid DBus introspection XML for a ``method``.

        :param element: The parsed XML element.
        :type element: :class:`xml.etree.ElementTree.Element`
        :param is_root: Whether this is the root node
        :type is_root: bool

        :raises:
            - :class:`InvalidIntrospectionError <dbus_fast.InvalidIntrospectionError>` - If the XML tree is not valid introspection data.
        """
        name = element.attrib.get("name")
        if not name:
            raise InvalidIntrospectionError('interfaces must have a "name" attribute')

        in_args = []
        out_args = []

        for child in element:
            if child.tag == "arg":
                direction = ArgDirection(child.attrib.get("direction", "in"))
                arg = Arg.from_xml(child, direction)
                if direction == ArgDirection.IN:
                    in_args.append(arg)
                elif direction == ArgDirection.OUT:
                    out_args.append(arg)

        return Method(name, in_args, out_args)

    def to_xml(self) -> ET.Element:
        """Convert this :class:`Method` into an :class:`xml.etree.ElementTree.Element`."""
        element = ET.Element("method")
        element.set("name", self.name)

        for arg in self.in_args:
            element.append(arg.to_xml())
        for arg in self.out_args:
            element.append(arg.to_xml())

        return element


class Property:
    """A class that represents a DBus property exposed on an
    :class:`Interface`.

    :ivar name: The name of this property.
    :vartype name: str
    :ivar signature: The signature string for this property. Must be a single complete type.
    :vartype signature: str
    :ivar access: Whether this property is readable and writable.
    :vartype access: :class:`PropertyAccess <dbus_fast.PropertyAccess>`
    :ivar type: The parsed type of this property.
    :vartype type: :class:`SignatureType <dbus_fast.SignatureType>`

    :raises:
        - :class:`InvalidIntrospectionError <dbus_fast.InvalidIntrospectionError>` - If the property is not a single complete type.
        - :class `InvalidSignatureError <dbus_fast.InvalidSignatureError>` - If the given signature is not valid.
        - :class: `InvalidMemberNameError <dbus_fast.InvalidMemberNameError>` - If the member name is not valid.
    """

    def __init__(
        self,
        name: str,
        signature: str,
        access: PropertyAccess = PropertyAccess.READWRITE,
    ):
        assert_member_name_valid(name)

        tree = get_signature_tree(signature)
        if len(tree.types) != 1:
            raise InvalidIntrospectionError(
                f"properties must have a single complete type. (has {len(tree.types)} types)"
            )

        self.name = name
        self.signature = signature
        self.access = access
        self.type = tree.types[0]

    def from_xml(element):
        """Convert an :class:`xml.etree.ElementTree.Element` to a :class:`Property`.

        The element must be valid DBus introspection XML for a ``property``.

        :param element: The parsed XML element.
        :type element: :class:`xml.etree.ElementTree.Element`

        :raises:
            - :class:`InvalidIntrospectionError <dbus_fast.InvalidIntrospectionError>` - If the XML tree is not valid introspection data.
        """
        name = element.attrib.get("name")
        signature = element.attrib.get("type")
        access = PropertyAccess(element.attrib.get("access", "readwrite"))

        if not name:
            raise InvalidIntrospectionError('properties must have a "name" attribute')
        if not signature:
            raise InvalidIntrospectionError('properties must have a "type" attribute')

        return Property(name, signature, access)

    def to_xml(self) -> ET.Element:
        """Convert this :class:`Property` into an :class:`xml.etree.ElementTree.Element`."""
        element = ET.Element("property")
        element.set("name", self.name)
        element.set("type", self.signature)
        element.set("access", self.access.value)
        return element


class Interface:
    """A class that represents a DBus interface exported on on object path.

    Contains information about the methods, signals, and properties exposed on
    this interface.

    :ivar name: The name of this interface.
    :vartype name: str
    :ivar methods: A list of methods exposed on this interface.
    :vartype methods: list(:class:`Method`)
    :ivar signals: A list of signals exposed on this interface.
    :vartype signals: list(:class:`Signal`)
    :ivar properties: A list of properties exposed on this interface.
    :vartype properties: list(:class:`Property`)

    :raises:
        - :class:`InvalidInterfaceNameError <dbus_fast.InvalidInterfaceNameError>` - If the name is not a valid interface name.
    """

    def __init__(
        self,
        name: str,
        methods: Optional[List[Method]] = None,
        signals: Optional[List[Signal]] = None,
        properties: Optional[List[Property]] = None,
    ):
        assert_interface_name_valid(name)

        self.name = name
        self.methods = methods if methods is not None else []
        self.signals = signals if signals is not None else []
        self.properties = properties if properties is not None else []

    @staticmethod
    def from_xml(element: ET.Element) -> "Interface":
        """Convert a :class:`xml.etree.ElementTree.Element` into a
        :class:`Interface`.

        The element must be valid DBus introspection XML for an ``interface``.

        :param element: The parsed XML element.
        :type element: :class:`xml.etree.ElementTree.Element`

        :raises:
            - :class:`InvalidIntrospectionError <dbus_fast.InvalidIntrospectionError>` - If the XML tree is not valid introspection data.
        """
        name = element.attrib.get("name")
        if not name:
            raise InvalidIntrospectionError('interfaces must have a "name" attribute')

        interface = Interface(name)

        for child in element:
            if child.tag == "method":
                interface.methods.append(Method.from_xml(child))
            elif child.tag == "signal":
                interface.signals.append(Signal.from_xml(child))
            elif child.tag == "property":
                interface.properties.append(Property.from_xml(child))

        return interface

    def to_xml(self) -> ET.Element:
        """Convert this :class:`Interface` into an :class:`xml.etree.ElementTree.Element`."""
        element = ET.Element("interface")
        element.set("name", self.name)

        for method in self.methods:
            element.append(method.to_xml())
        for signal in self.signals:
            element.append(signal.to_xml())
        for prop in self.properties:
            element.append(prop.to_xml())

        return element


class Node:
    """A class that represents a node in an object path in introspection data.

    A node contains information about interfaces exported on this path and
    child nodes. A node can be converted to and from introspection XML exposed
    through the ``org.freedesktop.DBus.Introspectable`` standard DBus
    interface.

    This class is an essential building block for a high-level DBus interface.
    This is the underlying data structure for the :class:`ProxyObject
    <dbus_fast.proxy_object.BaseProxyInterface>`.  A :class:`ServiceInterface
    <dbus_fast.service.ServiceInterface>` definition is converted to this class
    to expose XML on the introspectable interface.

    :ivar interfaces: A list of interfaces exposed on this node.
    :vartype interfaces: list(:class:`Interface <dbus_fast.introspection.Interface>`)
    :ivar nodes: A list of child nodes.
    :vartype nodes: list(:class:`Node`)
    :ivar name: The object path of this node.
    :vartype name: str
    :ivar is_root: Whether this is the root node. False if it is a child node.
    :vartype is_root: bool

    :raises:
        - :class:`InvalidIntrospectionError <dbus_fast.InvalidIntrospectionError>` - If the name is not a valid node name.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        interfaces: Optional[List[Interface]] = None,
        is_root: bool = True,
    ):
        if not is_root and not name:
            raise InvalidIntrospectionError('child nodes must have a "name" attribute')

        self.interfaces = interfaces if interfaces is not None else []
        self.nodes = []
        self.name = name
        self.is_root = is_root

    @staticmethod
    def from_xml(element: ET.Element, is_root: bool = False):
        """Convert an :class:`xml.etree.ElementTree.Element` to a :class:`Node`.

        The element must be valid DBus introspection XML for a ``node``.

        :param element: The parsed XML element.
        :type element: :class:`xml.etree.ElementTree.Element`
        :param is_root: Whether this is the root node
        :type is_root: bool

        :raises:
            - :class:`InvalidIntrospectionError <dbus_fast.InvalidIntrospectionError>` - If the XML tree is not valid introspection data.
        """
        node = Node(element.attrib.get("name"), is_root=is_root)

        for child in element:
            if child.tag == "interface":
                node.interfaces.append(Interface.from_xml(child))
            elif child.tag == "node":
                node.nodes.append(Node.from_xml(child))

        return node

    @staticmethod
    def parse(data: str) -> "Node":
        """Parse XML data as a string into a :class:`Node`.

        The string must be valid DBus introspection XML.

        :param data: The XMl string.
        :type data: str

        :raises:
            - :class:`InvalidIntrospectionError <dbus_fast.InvalidIntrospectionError>` - If the string is not valid introspection data.
        """
        element = ET.fromstring(data)
        if element.tag != "node":
            raise InvalidIntrospectionError(
                'introspection data must have a "node" for the root element'
            )

        return Node.from_xml(element, is_root=True)

    def to_xml(self) -> ET.Element:
        """Convert this :class:`Node` into an :class:`xml.etree.ElementTree.Element`."""
        element = ET.Element("node")

        if self.name:
            element.set("name", self.name)

        for interface in self.interfaces:
            element.append(interface.to_xml())
        for node in self.nodes:
            element.append(node.to_xml())

        return element

    def tostring(self) -> str:
        """Convert this :class:`Node` into a DBus introspection XML string."""
        header = '<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"\n"http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">\n'

        def indent(elem, level=0):
            i = "\n" + level * "    "
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + "  "
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
                for elem in elem:
                    indent(elem, level + 1)
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i

        xml = self.to_xml()
        indent(xml)
        return header + ET.tostring(xml, encoding="unicode").rstrip()

    @staticmethod
    def default(name: Optional[str] = None) -> "Node":
        """Create a :class:`Node` with the default interfaces supported by this library.

        The default interfaces include:

        * ``org.freedesktop.DBus.Introspectable``
        * ``org.freedesktop.DBus.Peer``
        * ``org.freedesktop.DBus.Properties``
        * ``org.freedesktop.DBus.ObjectManager``
        """
        return Node(
            name,
            is_root=True,
            interfaces=[
                Interface(
                    "org.freedesktop.DBus.Introspectable",
                    methods=[
                        Method(
                            "Introspect", out_args=[Arg("s", ArgDirection.OUT, "data")]
                        )
                    ],
                ),
                Interface(
                    "org.freedesktop.DBus.Peer",
                    methods=[
                        Method(
                            "GetMachineId",
                            out_args=[Arg("s", ArgDirection.OUT, "machine_uuid")],
                        ),
                        Method("Ping"),
                    ],
                ),
                Interface(
                    "org.freedesktop.DBus.Properties",
                    methods=[
                        Method(
                            "Get",
                            in_args=[
                                Arg("s", ArgDirection.IN, "interface_name"),
                                Arg("s", ArgDirection.IN, "property_name"),
                            ],
                            out_args=[Arg("v", ArgDirection.OUT, "value")],
                        ),
                        Method(
                            "Set",
                            in_args=[
                                Arg("s", ArgDirection.IN, "interface_name"),
                                Arg("s", ArgDirection.IN, "property_name"),
                                Arg("v", ArgDirection.IN, "value"),
                            ],
                        ),
                        Method(
                            "GetAll",
                            in_args=[Arg("s", ArgDirection.IN, "interface_name")],
                            out_args=[Arg("a{sv}", ArgDirection.OUT, "props")],
                        ),
                    ],
                    signals=[
                        Signal(
                            "PropertiesChanged",
                            args=[
                                Arg("s", ArgDirection.OUT, "interface_name"),
                                Arg("a{sv}", ArgDirection.OUT, "changed_properties"),
                                Arg("as", ArgDirection.OUT, "invalidated_properties"),
                            ],
                        )
                    ],
                ),
                Interface(
                    "org.freedesktop.DBus.ObjectManager",
                    methods=[
                        Method(
                            "GetManagedObjects",
                            out_args=[
                                Arg(
                                    "a{oa{sa{sv}}}",
                                    ArgDirection.OUT,
                                    "objpath_interfaces_and_properties",
                                )
                            ],
                        ),
                    ],
                    signals=[
                        Signal(
                            "InterfacesAdded",
                            args=[
                                Arg("o", ArgDirection.OUT, "object_path"),
                                Arg(
                                    "a{sa{sv}}",
                                    ArgDirection.OUT,
                                    "interfaces_and_properties",
                                ),
                            ],
                        ),
                        Signal(
                            "InterfacesRemoved",
                            args=[
                                Arg("o", ArgDirection.OUT, "object_path"),
                                Arg("as", ArgDirection.OUT, "interfaces"),
                            ],
                        ),
                    ],
                ),
            ],
        )
