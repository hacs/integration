# -*- coding: utf-8 -*-
"""DIDL-Lite (Digital Item Declaration Language) tools for Python."""
# pylint: disable=too-many-lines

from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from xml.etree import ElementTree as ET

import defusedxml.ElementTree

from .utils import (
    NAMESPACES,
    didl_property_def_key,
    didl_property_key,
    expand_namespace_tag,
    split_namespace_tag,
    to_camel_case,
)

TDO = TypeVar("TDO", bound="DidlObject")  # pylint: disable=invalid-name
TC = TypeVar("TC", bound="Container")  # pylint: disable=invalid-name
TD = TypeVar("TD", bound="Descriptor")  # pylint: disable=invalid-name
TR = TypeVar("TR", bound="Resource")  # pylint: disable=invalid-name


class DidlLiteException(Exception):
    """DIDL Lite Exception."""


# region: DidlObjects

# upnp_class to python type mapping
_upnp_class_map: Dict[str, Type["DidlObject"]] = {}
_upnp_class_map_lowercase: Dict[str, Type["DidlObject"]] = {}


class DidlObject:
    """DIDL Object."""

    tag: Optional[str] = None
    upnp_class: str = "object"
    didl_properties_defs: List[Tuple[str, str, str]] = [
        ("didl_lite", "@id", "R"),
        ("didl_lite", "@parentID", "R"),
        ("didl_lite", "@restricted", "R"),
        ("dc", "title", "R"),
        ("upnp", "class", "R"),
        ("dc", "creator", "O"),
        ("didl_lite", "res", "O"),
        ("upnp", "writeStatus", "O"),
    ]

    id: str
    parent_id: str
    res: List["Resource"]
    xml_el: Optional[ET.Element]
    descriptors: Sequence["Descriptor"]

    @classmethod
    def __init_subclass__(cls: Type["DidlObject"], **kwargs: Any) -> None:
        """Create mapping of upnp_class to Python type for fast lookup."""
        super().__init_subclass__(**kwargs)
        assert cls.upnp_class not in _upnp_class_map
        assert cls.upnp_class.lower() not in _upnp_class_map_lowercase
        _upnp_class_map[cls.upnp_class] = cls
        _upnp_class_map_lowercase[cls.upnp_class.lower()] = cls

    def __init__(
        self,
        id: str = "",
        parent_id: str = "",
        descriptors: Optional[Sequence["Descriptor"]] = None,
        xml_el: Optional[ET.Element] = None,
        strict: bool = True,
        **properties: Any,
    ) -> None:
        """Initialize."""
        # pylint: disable=invalid-name,redefined-builtin,too-many-arguments
        properties["id"] = id
        properties["parent_id"] = parent_id
        properties["class"] = self.upnp_class
        properties["res"] = properties.get("res") or properties.get("resources") or []
        if "resources" in properties:
            del properties["resources"]
        self._ensure_required_properties(strict, properties)
        self._set_property_defaults()
        self._set_properties(properties)

        self.xml_el = xml_el
        self.descriptors = descriptors if descriptors else []

    def _ensure_required_properties(
        self, strict: bool, properties: Mapping[str, Any]
    ) -> None:
        """Check if all required properties are given."""
        if not strict:
            return

        python_property_keys = {didl_property_key(key) for key in properties}

        for property_def in self.didl_properties_defs:
            key = didl_property_def_key(property_def)
            if property_def[2] == "R" and key not in python_property_keys:
                raise DidlLiteException(key + " is mandatory")

    def _set_property_defaults(self) -> None:
        """Ensure we have default/known slots, and set them all to None."""
        for property_def in self.didl_properties_defs:
            key = didl_property_def_key(property_def)
            setattr(self, key, None)

    def _set_properties(self, properties: Mapping[str, Any]) -> None:
        """Set attributes from properties."""
        for key, value in properties.items():
            setattr(self, key, value)

    @classmethod
    def from_xml(cls: Type[TDO], xml_el: ET.Element, strict: bool = True) -> TDO:
        """
        Initialize from an XML node.

        I.e., parse XML and return instance.
        """
        # pylint: disable=too-many-locals
        properties = {}  # type: Dict[str, Any]

        # attributes
        for attr_key, attr_value in xml_el.attrib.items():
            key = to_camel_case(attr_key)
            properties[key] = attr_value

        # child-nodes
        for xml_child_node in xml_el:
            if xml_child_node.tag == expand_namespace_tag("didl_lite:res"):
                continue

            _, tag = split_namespace_tag(xml_child_node.tag)
            key = to_camel_case(tag)
            value = xml_child_node.text
            properties[key] = value

            # attributes of child nodes
            parent_key = key
            for attr_key, attr_value in xml_child_node.attrib.items():
                key = parent_key + "_" + to_camel_case(attr_key)
                properties[key] = attr_value

        # resources
        resources = []
        for res_el in xml_el.findall("./didl_lite:res", NAMESPACES):
            resource = Resource.from_xml(res_el)
            resources.append(resource)
        properties["res"] = properties["resources"] = resources

        # descriptors
        descriptors = []
        for desc_el in xml_el.findall("./didl_lite:desc", NAMESPACES):
            descriptor = Descriptor.from_xml(desc_el)
            descriptors.append(descriptor)

        return cls(xml_el=xml_el, descriptors=descriptors, strict=strict, **properties)

    def to_xml(self) -> ET.Element:
        """Convert self to XML Element."""
        assert self.tag is not None
        item_el = ET.Element(self.tag)
        elements = {"": item_el}

        # properties
        for property_def in self.didl_properties_defs:
            if "@" in property_def[1]:
                continue
            key = didl_property_def_key(property_def)

            if (
                getattr(self, key) is None or key == "res"
            ):  # no resources, handled later on
                continue

            tag = property_def[0] + ":" + property_def[1]
            property_el = ET.Element(tag, {})
            property_el.text = getattr(self, key)
            item_el.append(property_el)
            elements[property_def[1]] = property_el

        # attributes and property@attributes
        for property_def in self.didl_properties_defs:
            if "@" not in property_def[1]:
                continue

            key = didl_property_def_key(property_def)
            value = getattr(self, key)
            if value is None:
                continue

            el_name, attr_name = property_def[1].split("@")
            property_el = elements[el_name]
            property_el.attrib[attr_name] = value

        # resource
        for resource in self.resources:
            res_el = resource.to_xml()
            item_el.append(res_el)

        # descriptor
        for descriptor in self.descriptors:
            desc_el = descriptor.to_xml()
            item_el.append(desc_el)

        return item_el

    def __getattr__(self, name: str) -> Any:
        """Get attribute, modifying case as needed."""
        if name == "resources":
            return getattr(self, "res")
        if name in self.__dict__:
            return self.__dict__[name]
        cleaned_name = didl_property_key(name)
        if cleaned_name not in self.__dict__:
            raise AttributeError(name)
        return self.__dict__[cleaned_name]

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute, modifying case as needed."""
        if name not in self.__dict__:
            # Redirect to the lower_camel_case version if it's already set,
            # which is the case for all defined didl properties.
            cleaned_name = didl_property_key(name)
            if cleaned_name in self.__dict__:
                name = cleaned_name
        self.__dict__[name] = value

    def __repr__(self) -> str:
        """Evaluatable string representation of this object."""
        class_name = type(self).__name__
        attr = ", ".join(
            f"{key}={val!r}"
            for key, val in self.__dict__.items()
            if key not in ("class", "xml_el")
        )
        return f"{class_name}({attr})"


# region: items
class Item(DidlObject):
    """DIDL Item."""

    # pylint: disable=too-few-public-methods

    tag = "item"
    upnp_class = "object.item"
    didl_properties_defs = DidlObject.didl_properties_defs + [
        ("didl_lite", "@refID", "O"),  # actually, R, but ignore for now
        ("upnp", "bookmarkID", "O"),
    ]


class ImageItem(Item):
    """DIDL Image Item."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.item.imageItem"
    didl_properties_defs = Item.didl_properties_defs + [
        ("upnp", "longDescription", "O"),
        ("upnp", "storageMedium", "O"),
        ("upnp", "rating", "O"),
        ("dc", "description", "O"),
        ("dc", "publisher", "O"),
        ("dc", "date", "O"),
        ("dc", "rights", "O"),
    ]


class Photo(ImageItem):
    """DIDL Photo."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.item.imageItem.photo"
    didl_properties_defs = ImageItem.didl_properties_defs + [
        ("upnp", "album", "O"),
    ]


class AudioItem(Item):
    """DIDL Audio Item."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.item.audioItem"
    didl_properties_defs = Item.didl_properties_defs + [
        ("upnp", "genre", "O"),
        ("dc", "description", "O"),
        ("upnp", "longDescription", "O"),
        ("dc", "publisher", "O"),
        ("dc", "language", "O"),
        ("dc", "relation", "O"),
        ("dc", "rights", "O"),
    ]


class MusicTrack(AudioItem):
    """DIDL Music Track."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.item.audioItem.musicTrack"
    didl_properties_defs = AudioItem.didl_properties_defs + [
        ("upnp", "artist", "O"),
        ("upnp", "album", "O"),
        ("upnp", "originalTrackNumber", "O"),
        ("upnp", "playlist", "O"),
        ("upnp", "storageMedium", "O"),
        ("dc", "contributor", "O"),
        ("dc", "date", "O"),
    ]


class AudioBroadcast(AudioItem):
    """DIDL Audio Broadcast."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.item.audioItem.audioBroadcast"
    didl_properties_defs = AudioItem.didl_properties_defs + [
        ("upnp", "region", "O"),
        ("upnp", "radioCallSign", "O"),
        ("upnp", "radioStationID", "O"),
        ("upnp", "radioBand", "O"),
        ("upnp", "channelNr", "O"),
        ("upnp", "signalStrength", "O"),
        ("upnp", "signalLocked", "O"),
        ("upnp", "tuned", "O"),
        ("upnp", "recordable", "O"),
    ]


class AudioBook(AudioItem):
    """DIDL Audio Book."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.item.audioItem.audioBook"
    didl_properties_defs = AudioItem.didl_properties_defs + [
        ("upnp", "storageMedium", "O"),
        ("upnp", "producer", "O"),
        ("dc", "contributor", "O"),
        ("dc", "date", "O"),
    ]


class VideoItem(Item):
    """DIDL Video Item."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.item.videoItem"
    didl_properties_defs = Item.didl_properties_defs + [
        ("upnp", "genre", "O"),
        ("upnp", "genre@id", "O"),
        ("upnp", "genre@type", "O"),
        ("upnp", "longDescription", "O"),
        ("upnp", "producer", "O"),
        ("upnp", "rating", "O"),
        ("upnp", "actor", "O"),
        ("upnp", "director", "O"),
        ("dc", "description", "O"),
        ("dc", "publisher", "O"),
        ("dc", "language", "O"),
        ("dc", "relation", "O"),
        ("upnp", "playbackCount", "O"),
        ("upnp", "lastPlaybackTime", "O"),
        ("upnp", "lastPlaybackPosition", "O"),
        ("upnp", "recordedDayOfWeek", "O"),
        ("upnp", "srsRecordScheduleID", "O"),
    ]


class Movie(VideoItem):
    """DIDL Movie."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.item.videoItem.movie"
    didl_properties_defs = VideoItem.didl_properties_defs + [
        ("upnp", "storageMedium", "O"),
        ("upnp", "DVDRegionCode", "O"),
        ("upnp", "channelName", "O"),
        ("upnp", "scheduledStartTime", "O"),
        ("upnp", "scheduledEndTime", "O"),
        ("upnp", "programTitle", "O"),
        ("upnp", "seriesTitle", "O"),
        ("upnp", "episodeCount", "O"),
        ("upnp", "episodeNumber", "O"),
        ("upnp", "episodeSeason", "O"),
    ]


class VideoBroadcast(VideoItem):
    """DIDL Video Broadcast."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.item.videoItem.videoBroadcast"
    didl_properties_defs = VideoItem.didl_properties_defs + [
        ("upnp", "icon", "O"),
        ("upnp", "region", "O"),
        ("upnp", "channelNr", "O"),
        ("upnp", "signalStrength", "O"),
        ("upnp", "signalLocked", "O"),
        ("upnp", "tuned", "O"),
        ("upnp", "recordable", "O"),
        ("upnp", "callSign", "O"),
        ("upnp", "price", "O"),
        ("upnp", "payPerView", "O"),
    ]


class MusicVideoClip(VideoItem):
    """DIDL Music Video Clip."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.item.videoItem.musicVideoClip"
    didl_properties_defs = VideoItem.didl_properties_defs + [
        ("upnp", "artist", "O"),
        ("upnp", "storageMedium", "O"),
        ("upnp", "album", "O"),
        ("upnp", "scheduledStartTime", "O"),
        ("upnp", "scheduledStopTime", "O"),
        # ('upnp', 'director', 'O'),  # duplicate in standard
        ("dc", "contributor", "O"),
        ("dc", "date", "O"),
    ]


class PlaylistItem(Item):
    """DIDL Playlist Item."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.item.playlistItem"
    didl_properties_defs = Item.didl_properties_defs + [
        ("upnp", "artist", "O"),
        ("upnp", "genre", "O"),
        ("upnp", "longDescription", "O"),
        ("upnp", "storageMedium", "O"),
        ("dc", "description", "O"),
        ("dc", "date", "O"),
        ("dc", "language", "O"),
    ]


class TextItem(Item):
    """DIDL Text Item."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.item.textItem"
    didl_properties_defs = Item.didl_properties_defs + [
        ("upnp", "author", "O"),
        ("upnp", "res@protection", "O"),
        ("upnp", "longDescription", "O"),
        ("upnp", "storageMedium", "O"),
        ("upnp", "rating", "O"),
        ("dc", "description", "O"),
        ("dc", "publisher", "O"),
        ("dc", "contributor", "O"),
        ("dc", "date", "O"),
        ("dc", "relation", "O"),
        ("dc", "language", "O"),
        ("dc", "rights", "O"),
    ]


class BookmarkItem(Item):
    """DIDL Bookmark Item."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.item.bookmarkItem"
    didl_properties_defs = Item.didl_properties_defs + [
        ("upnp", "bookmarkedObjectID", "R"),
        ("upnp", "neverPlayable", "O"),
        ("upnp", "deviceUDN", "R"),
        ("upnp", "serviceType", "R"),
        ("upnp", "serviceId", "R"),
        ("dc", "date", "O"),
        ("dc", "stateVariableCollection", "R"),
    ]


class EpgItem(Item):
    """DIDL EPG Item."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.item.epgItem"
    didl_properties_defs = Item.didl_properties_defs + [
        ("upnp", "channelGroupName", "O"),
        ("upnp", "channelGroupName@id", "O"),
        ("upnp", "epgProviderName", "O"),
        ("upnp", "serviceProvider", "O"),
        ("upnp", "channelName", "O"),
        ("upnp", "channelNr", "O"),
        ("upnp", "programTitle", "O"),
        ("upnp", "seriesTitle", "O"),
        ("upnp", "programID", "O"),
        ("upnp", "programID@type", "O"),
        ("upnp", "seriesID", "O"),
        ("upnp", "seriesID@type", "O"),
        ("upnp", "channelID", "O"),
        ("upnp", "channelID@type", "O"),
        ("upnp", "channelID@distriNetworkName", "O"),
        ("upnp", "channelID@distriNetworkID", "O"),
        ("upnp", "episodeType", "O"),
        ("upnp", "episodeCount", "O"),
        ("upnp", "episodeNumber", "O"),
        ("upnp", "episodeSeason", "O"),
        ("upnp", "programCode", "O"),
        ("upnp", "programCode@type", "O"),
        ("upnp", "rating", "O"),
        ("upnp", "rating@type", "O"),
        ("upnp", "rating@advice", "O"),
        ("upnp", "rating@equivalentAge", "O"),
        ("upnp", "recommendationID", "O"),
        ("upnp", "recommendationID@type", "O"),
        ("upnp", "genre", "O"),
        ("upnp", "genre@id", "O"),
        ("upnp", "genre@extended", "O"),
        ("upnp", "artist", "O"),
        ("upnp", "artist@role", "O"),
        ("upnp", "actor", "O"),
        ("upnp", "actor@role", "O"),
        ("upnp", "author", "O"),
        ("upnp", "author@role", "O"),
        ("upnp", "producer", "O"),
        ("upnp", "director", "O"),
        ("dc", "publisher", "O"),
        ("dc", "contributor", "O"),
        ("upnp", "callSign", "O"),
        ("upnp", "networkAffiliation", "O"),
        # ('upnp', 'serviceProvider', 'O'),  # duplicate in standard
        ("upnp", "price", "O"),
        ("upnp", "price@currency", "O"),
        ("upnp", "payPerView", "O"),
        # ('upnp', 'epgProviderName', 'O'),  # duplicate in standard
        ("dc", "description", "O"),
        ("upnp", "longDescription", "O"),
        ("upnp", "icon", "O"),
        ("upnp", "region", "O"),
        ("upnp", "rights", "O"),
        ("dc", "language", "O"),
        ("dc", "relation", "O"),
        ("upnp", "scheduledStartTime", "O"),
        ("upnp", "scheduledEndTime", "O"),
        ("upnp", "recordable", "O"),
        ("upnp", "foreignMetadata", "O"),
    ]


class AudioProgram(EpgItem):
    """DIDL Audio Program."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.item.epgItem.audioProgram"
    didl_properties_defs = Item.didl_properties_defs + [
        ("upnp", "radioCallSign", "O"),
        ("upnp", "radioStationID", "O"),
        ("upnp", "radioBand", "O"),
    ]


class VideoProgram(EpgItem):
    """DIDL Video Program."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.item.epgItem.videoProgram"
    didl_properties_defs = Item.didl_properties_defs + [
        ("upnp", "price", "O"),
        ("upnp", "price@currency", "O"),
        ("upnp", "payPerView", "O"),
    ]


# endregion


# region: containers
class Container(DidlObject, list):
    """DIDL Container."""

    # pylint: disable=too-few-public-methods

    tag = "container"
    upnp_class = "object.container"
    didl_properties_defs = DidlObject.didl_properties_defs + [
        ("didl_lite", "@childCount", "O"),
        ("upnp", "createClass", "O"),
        ("upnp", "searchClass", "O"),
        ("didl_lite", "@searchable", "O"),
        ("didl_lite", "@neverPlayable", "O"),
    ]

    def __init__(
        self,
        id: str = "",
        parent_id: str = "",
        descriptors: Optional[Sequence["Descriptor"]] = None,
        xml_el: Optional[ET.Element] = None,
        strict: bool = True,
        children: Iterable[DidlObject] = (),
        **properties: Any,
    ) -> None:
        """Initialize."""
        # pylint: disable=redefined-builtin,too-many-arguments
        super().__init__(id, parent_id, descriptors, xml_el, strict, **properties)
        self.extend(children)

    @classmethod
    def from_xml(cls: Type[TC], xml_el: ET.Element, strict: bool = True) -> TC:
        """
        Initialize from an XML node.

        I.e., parse XML and return instance.
        """
        instance = super().from_xml(xml_el, strict)

        # add all children
        didl_objects = from_xml_el(xml_el, strict)
        instance.extend(didl_objects)  # pylint: disable=no-member

        return instance

    def to_xml(self) -> ET.Element:
        """Convert self to XML Element."""
        container_el = super().to_xml()

        for didl_object in self:
            didl_object_el = didl_object.to_xml()
            container_el.append(didl_object_el)

        return container_el

    def __repr__(self) -> str:
        """Evaluatable string representation of this object."""
        class_name = type(self).__name__
        attr = ", ".join(
            f"{key}={val!r}"
            for key, val in self.__dict__.items()
            if key not in ("class", "xml_el")
        )
        children_repr = ", ".join(repr(child) for child in self)
        return f"{class_name}({attr}, children=[{children_repr}])"


class Person(Container):
    """DIDL Person."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.container.person"
    didl_properties_defs = Container.didl_properties_defs + [
        ("dc", "language", "O"),
    ]


class MusicArtist(Person):
    """DIDL Music Artist."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.container.person.musicArtist"
    didl_properties_defs = Container.didl_properties_defs + [
        ("upnp", "genre", "O"),
        ("upnp", "artistDiscographyURI", "O"),
    ]


class PlaylistContainer(Container):
    """DIDL Playlist Container."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.container.playlistContainer"
    didl_properties_defs = Container.didl_properties_defs + [
        ("upnp", "artist", "O"),
        ("upnp", "genre", "O"),
        ("upnp", "longDescription", "O"),
        ("upnp", "producer", "O"),
        ("upnp", "storageMedium", "O"),
        ("dc", "description", "O"),
        ("dc", "contributor", "O"),
        ("dc", "date", "O"),
        ("dc", "language", "O"),
        ("dc", "rights", "O"),
    ]


class Album(Container):
    """DIDL Album."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.container.album"
    didl_properties_defs = Container.didl_properties_defs + [
        ("upnp", "storageMedium", "O"),
        ("dc", "longDescription", "O"),
        ("dc", "description", "O"),
        ("dc", "publisher", "O"),
        ("dc", "contributor", "O"),
        ("dc", "date", "O"),
        ("dc", "relation", "O"),
        ("dc", "rights", "O"),
    ]


class MusicAlbum(Album):
    """DIDL Music Album."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.container.album.musicAlbum"
    didl_properties_defs = Container.didl_properties_defs + [
        ("upnp", "artist", "O"),
        ("upnp", "genre", "O"),
        ("upnp", "producer", "O"),
        ("upnp", "albumArtURI", "O"),
        ("upnp", "toc", "O"),
    ]


class PhotoAlbum(Album):
    """DIDL Photo Album."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.container.album.photoAlbum"
    didl_properties_defs = Container.didl_properties_defs + []


class Genre(Container):
    """DIDL Genre."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.container.genre"
    didl_properties_defs = Container.didl_properties_defs + [
        ("upnp", "genre", "O"),
        ("upnp", "longDescription", "O"),
        ("dc", "description", "O"),
    ]


class MusicGenre(Genre):
    """DIDL Music Genre."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.container.genre.musicGenre"
    didl_properties_defs = Container.didl_properties_defs + []


class MovieGenre(Genre):
    """DIDL Movie Genre."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.container.genre.movieGenre"
    didl_properties_defs = Container.didl_properties_defs + []


class ChannelGroup(Container):
    """DIDL Channel Group."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.container.channelGroup"
    didl_properties_defs = Container.didl_properties_defs + [
        ("upnp", "channelGroupName", "O"),
        ("upnp", "channelGroupName@id", "O"),
        ("upnp", "epgProviderName", "O"),
        ("upnp", "serviceProvider", "O"),
        ("upnp", "icon", "O"),
        ("upnp", "region", "O"),
    ]


class AudioChannelGroup(ChannelGroup):
    """DIDL Audio Channel Group."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.container.channelGroup.audioChannelGroup"
    didl_properties_defs = Container.didl_properties_defs + []


class VideoChannelGroup(ChannelGroup):
    """DIDL Video Channel Group."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.container.channelGroup.videoChannelGroup"
    didl_properties_defs = Container.didl_properties_defs + []


class EpgContainer(Container):
    """DIDL EPG Container."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.container.epgContainer"
    didl_properties_defs = Container.didl_properties_defs + [
        ("upnp", "channelGroupName", "O"),
        ("upnp", "channelGroupName@id", "O"),
        ("upnp", "epgProviderName", "O"),
        ("upnp", "serviceProvider", "O"),
        ("upnp", "channelName", "O"),
        ("upnp", "channelNr", "O"),
        ("upnp", "channelID", "O"),
        ("upnp", "channelID@type", "O"),
        ("upnp", "radioCallSign", "O"),
        ("upnp", "radioStationID", "O"),
        ("upnp", "radioBand", "O"),
        ("upnp", "callSign", "O"),
        ("upnp", "networkAffiliation", "O"),
        # ('upnp', 'serviceProvider', 'O'),  # duplicate in standard
        ("upnp", "price", "O"),
        ("upnp", "price@currency", "O"),
        ("upnp", "payPerView", "O"),
        # ('upnp', 'epgProviderName', 'O'),  # duplicate in standard
        ("upnp", "icon", "O"),
        ("upnp", "region", "O"),
        ("dc", "language", "O"),
        ("dc", "relation", "O"),
        ("upnp", "dateTimeRange", "O"),
    ]


class StorageSystem(Container):
    """DIDL Storage System."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.container.storageSystem"
    didl_properties_defs = Container.didl_properties_defs + [
        ("upnp", "storageTotal", "R"),
        ("upnp", "storageUsed", "R"),
        ("upnp", "storageFree", "R"),
        ("upnp", "storageMaxPartition", "R"),
        ("upnp", "storageMedium", "R"),
    ]


class StorageVolume(Container):
    """DIDL Storage Volume."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.container.storageVolume"
    didl_properties_defs = Container.didl_properties_defs + [
        ("upnp", "storageTotal", "R"),
        ("upnp", "storageUsed", "R"),
        ("upnp", "storageFree", "R"),
        ("upnp", "storageMedium", "R"),
    ]


class StorageFolder(Container):
    """DIDL Storage Folder."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.container.storageFolder"
    didl_properties_defs = Container.didl_properties_defs + [
        ("upnp", "storageUsed", "R"),
    ]


class BookmarkFolder(Container):
    """DIDL Bookmark Folder."""

    # pylint: disable=too-few-public-methods

    upnp_class = "object.container.bookmarkFolder"
    didl_properties_defs = Container.didl_properties_defs + [
        ("upnp", "genre", "O"),
        ("upnp", "longDescription", "O"),
        ("dc", "description", "O"),
    ]


# endregion


class Resource:
    """DIDL Resource."""

    # pylint: disable=too-few-public-methods,too-many-instance-attributes

    def __init__(
        self,
        uri: Optional[str],
        protocol_info: Optional[str],
        import_uri: Optional[str] = None,
        size: Optional[str] = None,
        duration: Optional[str] = None,
        bitrate: Optional[str] = None,
        sample_frequency: Optional[str] = None,
        bits_per_sample: Optional[str] = None,
        nr_audio_channels: Optional[str] = None,
        resolution: Optional[str] = None,
        color_depth: Optional[str] = None,
        protection: Optional[str] = None,
        xml_el: Optional[ET.Element] = None,
    ) -> None:
        """Initialize."""
        # pylint: disable=too-many-arguments
        self.uri = uri
        self.protocol_info = protocol_info
        self.import_uri = import_uri
        self.size = size
        self.duration = duration
        self.bitrate = bitrate
        self.sample_frequency = sample_frequency
        self.bits_per_sample = bits_per_sample
        self.nr_audio_channels = nr_audio_channels
        self.resolution = resolution
        self.color_depth = color_depth
        self.protection = protection
        self.xml_el = xml_el

    @classmethod
    def from_xml(cls: Type[TR], xml_el: ET.Element) -> TR:
        """Initialize from an XML node."""
        uri = xml_el.text
        protocol_info = xml_el.attrib.get("protocolInfo")
        import_uri = xml_el.attrib.get("importUri")
        size = xml_el.attrib.get("size")
        duration = xml_el.attrib.get("duration")
        bitrate = xml_el.attrib.get("bitrate")
        sample_frequency = xml_el.attrib.get("sampleFrequency")
        bits_per_sample = xml_el.attrib.get("bitsPerSample")
        nr_audio_channels = xml_el.attrib.get("nrAudioChannels")
        resolution = xml_el.attrib.get("resolution")
        color_depth = xml_el.attrib.get("colorDepth")
        protection = xml_el.attrib.get("protection")
        return cls(
            uri,
            protocol_info=protocol_info,
            import_uri=import_uri,
            size=size,
            duration=duration,
            bitrate=bitrate,
            sample_frequency=sample_frequency,
            bits_per_sample=bits_per_sample,
            nr_audio_channels=nr_audio_channels,
            resolution=resolution,
            color_depth=color_depth,
            protection=protection,
            xml_el=xml_el,
        )

    def to_xml(self) -> ET.Element:
        """Convert self to XML."""
        attribs = {
            "protocolInfo": self.protocol_info or "",
        }
        res_el = ET.Element("res", attribs)
        res_el.text = self.uri
        return res_el

    def __repr__(self) -> str:
        """Evaluatable string representation of this object."""
        class_name = type(self).__name__
        attr = ", ".join(
            f"{key}={val!r}"
            for key, val in self.__dict__.items()
            if val is not None and key != "xml_el"
        )
        return f"{class_name}({attr})"


class Descriptor:
    """DIDL Descriptor."""

    def __init__(
        self,
        id: str,
        name_space: str,
        type: Optional[str] = None,
        text: Optional[str] = None,
        xml_el: Optional[ET.Element] = None,
    ) -> None:
        """Initialize."""
        # pylint: disable=invalid-name,redefined-builtin,too-many-arguments
        self.id = id
        self.name_space = name_space
        self.type = type
        self.text = text
        self.xml_el = xml_el

    @classmethod
    def from_xml(cls: Type[TD], xml_el: ET.Element) -> TD:
        """Initialize from an XML node."""
        id_ = xml_el.attrib["id"]
        name_space = xml_el.attrib["nameSpace"]
        type_ = xml_el.attrib.get("type")
        text = xml_el.text
        return cls(id_, name_space, type=type_, text=text, xml_el=xml_el)

    def to_xml(self) -> ET.Element:
        """Convert self to XML."""
        attribs = {
            "id": self.id,
            "nameSpace": self.name_space,
        }
        if self.type is not None:
            attribs["type"] = self.type
        desc_el = ET.Element("desc", attribs)
        desc_el.text = self.text
        return desc_el

    def __getattr__(self, name: str) -> Any:
        """Get attribute."""
        if name not in self.__dict__:
            raise AttributeError(name)
        return self.__dict__[name]

    def __repr__(self) -> str:
        """Evaluatable string representation of this object."""
        class_name = type(self).__name__
        attr = ", ".join(
            f"{key}={val!r}"
            for key, val in self.__dict__.items()
            if val is not None and key != "xml_el"
        )
        return f"{class_name}({attr})"


# endregion


def to_xml_string(*objects: DidlObject) -> bytes:
    """Convert items to DIDL-Lite XML string."""
    root_el = ET.Element("DIDL-Lite", {})
    root_el.attrib["xmlns"] = NAMESPACES["didl_lite"]
    root_el.attrib["xmlns:dc"] = NAMESPACES["dc"]
    root_el.attrib["xmlns:upnp"] = NAMESPACES["upnp"]
    root_el.attrib["xmlns:sec"] = NAMESPACES["sec"]

    for didl_object in objects:
        didl_object_el = didl_object.to_xml()
        root_el.append(didl_object_el)

    return ET.tostring(root_el)


def from_xml_string(
    xml_string: str, strict: bool = True
) -> List[Union[DidlObject, Descriptor]]:
    """Convert XML string to DIDL Objects."""
    xml_el = defusedxml.ElementTree.fromstring(xml_string)
    return from_xml_el(xml_el, strict)


def from_xml_el(
    xml_el: ET.Element, strict: bool = True
) -> List[Union[DidlObject, Descriptor]]:
    """Convert XML Element to DIDL Objects."""
    didl_objects = []  # type: List[Union[DidlObject, Descriptor]]

    # items and containers, in order
    for child_el in xml_el:
        if child_el.tag != expand_namespace_tag(
            "didl_lite:item"
        ) and child_el.tag != expand_namespace_tag("didl_lite:container"):
            continue

        # construct item
        upnp_class = child_el.find("./upnp:class", NAMESPACES)
        if upnp_class is None or not upnp_class.text:
            continue
        didl_object_type = type_by_upnp_class(upnp_class.text, strict)
        if didl_object_type is None:
            if strict:
                raise DidlLiteException(f"upnp:class {upnp_class.text} is unknown")
            continue
        didl_object = didl_object_type.from_xml(child_el, strict)
        didl_objects.append(didl_object)

    # descriptors
    for desc_el in xml_el.findall("./didl_lite:desc", NAMESPACES):
        desc = Descriptor.from_xml(desc_el)
        didl_objects.append(desc)

    return didl_objects


# upnp_class to python type mapping
def type_by_upnp_class(
    upnp_class: str, strict: bool = True
) -> Optional[Type[DidlObject]]:
    """Get DidlObject-type by upnp_class.

    When strict is False, the upnp_class lookup will be done ignoring string
    case.
    """
    if strict:
        return _upnp_class_map.get(upnp_class)
    return _upnp_class_map_lowercase.get(upnp_class.lower())
