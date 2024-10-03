# -*- coding: utf-8 -*-
"""async_upnp_client.profiles.dlna module."""

# pylint: disable=too-many-lines

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum, IntEnum, IntFlag
from functools import lru_cache
from http import HTTPStatus
from mimetypes import guess_type
from time import monotonic as monotonic_timer
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Union,
)
from xml.sax.handler import ContentHandler, ErrorHandler
from xml.sax.xmlreader import AttributesImpl

from defusedxml.sax import parseString
from didl_lite import didl_lite

from async_upnp_client.client import UpnpService, UpnpStateVariable
from async_upnp_client.const import MIME_TO_UPNP_CLASS_MAPPING, HttpRequest
from async_upnp_client.exceptions import UpnpError
from async_upnp_client.profiles.profile import UpnpProfileDevice
from async_upnp_client.utils import absolute_url, str_to_time, time_to_str

_LOGGER = logging.getLogger(__name__)


DeviceState = Enum("DeviceState", "ON PLAYING PAUSED IDLE")


class TransportState(str, Enum):
    """Allowed values for DLNA AV Transport TransportState variable."""

    STOPPED = "STOPPED"
    PLAYING = "PLAYING"
    TRANSITIONING = "TRANSITIONING"
    PAUSED_PLAYBACK = "PAUSED_PLAYBACK"
    PAUSED_RECORDING = "PAUSED_RECORDING"
    RECORDING = "RECORDING"
    NO_MEDIA_PRESENT = "NO_MEDIA_PRESENT"
    VENDOR_DEFINED = "VENDOR_DEFINED"


class PlayMode(str, Enum):
    """Allowed values for DLNA AV Transport CurrentPlayMode variable."""

    NORMAL = "NORMAL"
    SHUFFLE = "SHUFFLE"
    REPEAT_ONE = "REPEAT_ONE"
    REPEAT_ALL = "REPEAT_ALL"
    RANDOM = "RANDOM"
    DIRECT_1 = "DIRECT_1"
    INTRO = "INTRO"
    VENDOR_DEFINED = "VENDOR_DEFINED"


class DlnaOrgOp(Enum):
    """DLNA.ORG_OP (Operations Parameter) flags."""

    NONE = 0
    RANGE = 0x01
    TIMESEEK = 0x10


class DlnaOrgCi(Enum):
    """DLNA.ORG_CI (Conversion Indicator) flags."""

    NONE = 0
    TRANSCODED = 1


class DlnaOrgPs(Enum):
    """DLNA.ORG_PS (PlaySpeed ) flags."""

    INVALID = 0
    NORMAL = 1


class DlnaOrgFlags(IntFlag):
    """
    DLNA.ORG_FLAGS flags.

    padded with 24 trailing 0s
    80000000  31  sender paced
    40000000  30  lsop time based seek supported
    20000000  29  lsop byte based seek supported
    10000000  28  playcontainer supported
     8000000  27  s0 increasing supported
     4000000  26  sN increasing supported
     2000000  25  rtsp pause supported
     1000000  24  streaming transfer mode supported
      800000  23  interactive transfer mode supported
      400000  22  background transfer mode supported
      200000  21  connection stalling supported
      100000  20  dlna version15 supported
    """

    SENDER_PACED = 1 << 31
    TIME_BASED_SEEK = 1 << 30
    BYTE_BASED_SEEK = 1 << 29
    PLAY_CONTAINER = 1 << 28
    S0_INCREASE = 1 << 27
    SN_INCREASE = 1 << 26
    RTSP_PAUSE = 1 << 25
    STREAMING_TRANSFER_MODE = 1 << 24
    INTERACTIVE_TRANSFERT_MODE = 1 << 23
    BACKGROUND_TRANSFERT_MODE = 1 << 22
    CONNECTION_STALL = 1 << 21
    DLNA_V15 = 1 << 20


class DlnaDmrEventContentHandler(ContentHandler):
    """Content Handler to parse DLNA DMR Event data."""

    def __init__(self) -> None:
        """Initialize."""
        super().__init__()
        self.changes: MutableMapping[str, MutableMapping[str, Any]] = {}
        self._current_instance: Optional[str] = None

    def startElement(self, name: str, attrs: AttributesImpl) -> None:
        """Handle startElement."""
        if "val" not in attrs:
            return

        if name == "InstanceID":
            self._current_instance = attrs.get("val", "0")
        else:
            current_instance = self._current_instance or "0"  # safety

            if current_instance not in self.changes:
                self.changes[current_instance] = {}

            # If channel is given, we're only interested in the Master channel.
            if attrs.get("channel") not in (None, "Master"):
                return

            # Strip namespace prefix.
            if ":" in name:
                index = name.find(":") + 1
                name = name[index:]

            self.changes[current_instance][name] = attrs.get("val")

    def endElement(self, name: str) -> None:
        """Handle endElement."""
        if name == "InstanceID":
            self._current_instance = None


class DlnaDmrEventErrorHandler(ErrorHandler):
    """Error handler which ignores errors."""

    def error(self, exception: BaseException) -> None:  # type: ignore
        """Handle error."""
        _LOGGER.debug("Error during parsing: %s", exception)

    def fatalError(self, exception: BaseException) -> None:  # type: ignore
        """Handle error."""
        _LOGGER.debug("Fatal error during parsing: %s", exception)


def _parse_last_change_event(text: str) -> Mapping[str, Mapping[str, str]]:
    """
    Parse a LastChange event.

    :param text Text to parse.

    :return Dict per Instance, containing changed state variables with values.
    """
    content_handler = DlnaDmrEventContentHandler()
    error_handler = DlnaDmrEventErrorHandler()
    parseString(text.encode(), content_handler, error_handler)
    return content_handler.changes


def dlna_handle_notify_last_change(state_var: UpnpStateVariable) -> None:
    """
    Handle changes to LastChange state variable.

    This expands all changed state variables in the LastChange state variable.
    Note that the callback is called twice:
    - for the original event;
    - for the expanded event, via this function.
    """
    if state_var.name != "LastChange":
        raise UpnpError("Call this only on state variable LastChange")

    event_data: Optional[str] = state_var.value
    if not event_data:
        _LOGGER.debug("No event data on state_variable")
        return

    changes = _parse_last_change_event(event_data)
    if "0" not in changes:
        _LOGGER.warning("Only InstanceID 0 is supported")
        return

    service = state_var.service
    changes_0 = changes["0"]
    service.notify_changed_state_variables(changes_0)


@lru_cache(maxsize=128)
def split_commas(input_: str) -> List[str]:
    """
    Split a string into a list of comma separated values.

    Strip whitespace and omit the empty string.
    """
    stripped = (item.strip() for item in input_.split(","))
    return [item for item in stripped if item]


@lru_cache(maxsize=128)
def _lower_split_commas(input_: str) -> Set[str]:
    """Lowercase version of split_commas."""
    return {a.lower() for a in split_commas(input_)}


@lru_cache
def _cached_from_xml_string(
    xml: str,
) -> List[Union[didl_lite.DidlObject, didl_lite.Descriptor]]:
    return didl_lite.from_xml_string(xml, strict=False)


class ConnectionManagerMixin(UpnpProfileDevice):
    """Mix-in to support ConnectionManager actions and state variables."""

    _SERVICE_TYPES = {
        "CM": {
            "urn:schemas-upnp-org:service:ConnectionManager:3",
            "urn:schemas-upnp-org:service:ConnectionManager:2",
            "urn:schemas-upnp-org:service:ConnectionManager:1",
        },
    }

    __did_first_update: bool = False

    async def async_update(self) -> None:
        """Retrieve latest data."""
        if not self.__did_first_update:
            await self._async_poll_state_variables("CM", "GetProtocolInfo")
            self.__did_first_update = True

    # region CM
    @property
    def has_get_protocol_info(self) -> bool:
        """Check if device can report its protocol info."""
        return self._action("CM", "GetProtocolInfo") is not None

    async def async_get_protocol_info(self) -> Mapping[str, List[str]]:
        """Get protocol info."""
        action = self._action("CM", "GetProtocolInfo")
        if not action:
            return {"source": [], "sink": []}

        protocol_info = await action.async_call()
        return {
            "source": split_commas(protocol_info["Source"]),
            "sink": split_commas(protocol_info["Sink"]),
        }

    @property
    def source_protocol_info(self) -> List[str]:
        """Supported source protocols."""
        state_var = self._state_variable("CM", "SourceProtocolInfo")
        if state_var is None or not state_var.value:
            return []

        return split_commas(state_var.value)

    @property
    def sink_protocol_info(self) -> List[str]:
        """Supported sink protocols."""
        state_var = self._state_variable("CM", "SinkProtocolInfo")
        if state_var is None or not state_var.value:
            return []

        return split_commas(state_var.value)

    # endregion


class DmrDevice(ConnectionManagerMixin, UpnpProfileDevice):
    """Representation of a DLNA DMR device."""

    # pylint: disable=too-many-public-methods

    DEVICE_TYPES = [
        "urn:schemas-upnp-org:device:MediaRenderer:1",
        "urn:schemas-upnp-org:device:MediaRenderer:2",
        "urn:schemas-upnp-org:device:MediaRenderer:3",
    ]

    SERVICE_IDS = frozenset(
        (
            "urn:upnp-org:serviceId:AVTransport",
            "urn:upnp-org:serviceId:ConnectionManager",
            "urn:upnp-org:serviceId:RenderingControl",
        )
    )

    _SERVICE_TYPES = {
        "RC": {
            "urn:schemas-upnp-org:service:RenderingControl:3",
            "urn:schemas-upnp-org:service:RenderingControl:2",
            "urn:schemas-upnp-org:service:RenderingControl:1",
        },
        "AVT": {
            "urn:schemas-upnp-org:service:AVTransport:3",
            "urn:schemas-upnp-org:service:AVTransport:2",
            "urn:schemas-upnp-org:service:AVTransport:1",
        },
        **ConnectionManagerMixin._SERVICE_TYPES,
    }

    _current_track_meta_data: Optional[didl_lite.DidlObject] = None
    _av_transport_uri_meta_data: Optional[didl_lite.DidlObject] = None
    __did_first_update: bool = False

    async def async_update(self, do_ping: bool = True) -> None:
        """Retrieve the latest data.

        :param do_ping: Poll device to check if it is available (online).
        """
        # pylint: disable=arguments-differ
        await super().async_update()

        # call GetTransportInfo/GetPositionInfo regularly
        avt_service = self._service("AVT")
        if avt_service:
            if not self.is_subscribed or do_ping:
                # CurrentTransportState is evented, so don't need to poll when subscribed
                await self._async_poll_state_variables(
                    "AVT", "GetTransportInfo", InstanceID=0
                )

            if self.transport_state in (
                TransportState.PLAYING,
                TransportState.PAUSED_PLAYBACK,
            ):
                # playing something, get position info
                # RelativeTimePosition is *never* evented, must always poll
                await self._async_poll_state_variables(
                    "AVT", "GetPositionInfo", InstanceID=0
                )
            if not self.is_subscribed or not self.__did_first_update:
                # Events won't be sent, so poll all state variables
                await self._async_poll_state_variables(
                    "AVT",
                    [
                        "GetMediaInfo",
                        "GetDeviceCapabilities",
                        "GetTransportSettings",
                        "GetCurrentTransportActions",
                    ],
                    InstanceID=0,
                )
                await self._async_poll_state_variables(
                    "RC", ["GetMute", "GetVolume"], InstanceID=0, Channel="Master"
                )
                self.__did_first_update = True
        elif do_ping:
            await self.profile_device.async_ping()

    def _on_event(
        self, service: UpnpService, state_variables: Sequence[UpnpStateVariable]
    ) -> None:
        """State variable(s) changed, perform callback(s)."""
        # handle DLNA specific event
        for state_variable in state_variables:
            if state_variable.name == "LastChange":
                dlna_handle_notify_last_change(state_variable)

        if service.service_id == "urn:upnp-org:serviceId:AVTransport":
            for state_variable in state_variables:
                if state_variable.name == "CurrentTrackMetaData":
                    self._update_current_track_meta_data(state_variable)
                if state_variable.name == "AVTransportURIMetaData":
                    self._update_av_transport_uri_metadata(state_variable)

        if self.on_event:
            # pylint: disable=not-callable
            self.on_event(service, state_variables)

    @property
    def state(self) -> DeviceState:
        """
        Get current state.

        This property is deprecated and will be removed in a future version!
        Please use `transport_state` instead.
        """
        state_var = self._state_variable("AVT", "TransportState")
        if not state_var:
            return DeviceState.ON

        state_value = (state_var.value or "").strip().lower()
        if state_value == "playing":
            return DeviceState.PLAYING
        if state_value in ("paused", "paused_playback"):
            return DeviceState.PAUSED

        return DeviceState.IDLE

    @property
    def transport_state(self) -> Optional[TransportState]:
        """Get transport state."""
        state_var = self._state_variable("AVT", "TransportState")
        if not state_var:
            return None

        state_value = (state_var.value or "").strip().upper()
        try:
            return TransportState[state_value]
        except KeyError:
            # Unknown state; return VENDOR_DEFINED.
            return TransportState.VENDOR_DEFINED

    @property
    def _has_current_transport_actions(self) -> bool:
        state_var = self._state_variable("AVT", "CurrentTransportActions")
        if not state_var:
            return False
        return state_var.value is not None or state_var.updated_at is not None

    @property
    def _current_transport_actions(self) -> Set[str]:
        state_var = self._state_variable("AVT", "CurrentTransportActions")
        if not state_var:
            return set()
        return _lower_split_commas(state_var.value or "")

    def _can_transport_action(self, action: str) -> bool:
        current_transport_actions = self._current_transport_actions
        return not current_transport_actions or action in current_transport_actions

    def _supports(self, var_name: str) -> bool:
        return (
            self._state_variable("RC", var_name) is not None
            and self._action("RC", f"Set{var_name}") is not None
        )

    def _level(self, var_name: str) -> Optional[float]:
        state_var = self._state_variable("RC", var_name)
        if state_var is None:
            _LOGGER.debug("Missing StateVariable RC/%s", var_name)
            return None

        value: Optional[float] = state_var.value
        if value is None:
            _LOGGER.debug("Got no value for %s", var_name)
            return None

        max_value = state_var.max_value or 100.0
        return min(value / max_value, 1.0)

    async def _async_set_level(
        self, var_name: str, level: float, **kwargs: Any
    ) -> None:
        action = self._action("RC", f"Set{var_name}")
        if not action:
            raise UpnpError(f"Missing Action RC/Set{var_name}")

        arg_name = f"Desired{var_name}"
        argument = action.argument(arg_name)
        if not argument:
            raise UpnpError(f"Missing Argument {arg_name} for Action RC/Set{var_name}")
        state_variable = argument.related_state_variable

        min_ = state_variable.min_value or 0
        max_ = state_variable.max_value or 100
        desired_level = int(min_ + level * (max_ - min_))

        args = kwargs.copy()
        args[arg_name] = desired_level
        await action.async_call(InstanceID=0, **args)

    # region RC/Picture
    @property
    def has_brightness_level(self) -> bool:
        """Check if device has brightness level controls."""
        return self._supports("Brightness")

    @property
    def brightness_level(self) -> Optional[float]:
        """Brightness level of the media player (0..1)."""
        return self._level("Brightness")

    async def async_set_brightness_level(self, brightness: float) -> None:
        """Set brightness level, range 0..1."""
        await self._async_set_level("Brightness", brightness)

    @property
    def has_contrast_level(self) -> bool:
        """Check if device has contrast level controls."""
        return self._supports("Contrast")

    @property
    def contrast_level(self) -> Optional[float]:
        """Contrast level of the media player (0..1)."""
        return self._level("Contrast")

    async def async_set_contrast_level(self, contrast: float) -> None:
        """Set contrast level, range 0..1."""
        await self._async_set_level("Contrast", contrast)

    @property
    def has_sharpness_level(self) -> bool:
        """Check if device has sharpness level controls."""
        return self._supports("Sharpness")

    @property
    def sharpness_level(self) -> Optional[float]:
        """Sharpness level of the media player (0..1)."""
        return self._level("Sharpness")

    async def async_set_sharpness_level(self, sharpness: float) -> None:
        """Set sharpness level, range 0..1."""
        await self._async_set_level("Sharpness", sharpness)

    @property
    def has_color_temperature_level(self) -> bool:
        """Check if device has color temperature level controls."""
        return self._supports("ColorTemperature")

    @property
    def color_temperature_level(self) -> Optional[float]:
        """Color temperature level of the media player (0..1)."""
        return self._level("ColorTemperature")

    async def async_set_color_temperature_level(self, color_temperature: float) -> None:
        """Set color temperature level, range 0..1."""
        # pylint: disable=invalid-name
        await self._async_set_level("ColorTemperature", color_temperature)

    # endregion

    # region RC/Volume
    @property
    def has_volume_level(self) -> bool:
        """Check if device has Volume level controls."""
        return self._supports("Volume")

    @property
    def volume_level(self) -> Optional[float]:
        """Volume level of the media player (0..1)."""
        return self._level("Volume")

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        await self._async_set_level("Volume", volume, Channel="Master")

    @property
    def has_volume_mute(self) -> bool:
        """Check if device has Volume mute controls."""
        return self._supports("Mute")

    @property
    def is_volume_muted(self) -> Optional[bool]:
        """Boolean if volume is currently muted."""
        state_var = self._state_variable("RC", "Mute")
        if not state_var:
            return None
        value: Optional[bool] = state_var.value
        if value is None:
            _LOGGER.debug("Got no value for Volume_mute")
            return None

        return value

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute the volume."""
        action = self._action("RC", "SetMute")
        if not action:
            raise UpnpError("Missing action RC/SetMute")
        desired_mute = bool(mute)
        await action.async_call(
            InstanceID=0, Channel="Master", DesiredMute=desired_mute
        )

    # endregion

    # region RC/Preset
    @property
    def has_presets(self) -> bool:
        """Check if device has control for rendering presets."""
        return (
            self._state_variable("RC", "PresetNameList") is not None
            and self._action("RC", "SelectPreset") is not None
        )

    @property
    def preset_names(self) -> List[str]:
        """List of valid preset names."""
        state_var = self._state_variable("RC", "PresetNameList")
        if state_var is None:
            _LOGGER.debug("Missing StateVariable RC/PresetNameList")
            return []

        value: Optional[str] = state_var.value
        if value is None:
            _LOGGER.debug("Got no value for PresetNameList")
            return []

        return split_commas(value)

    async def async_select_preset(self, preset_name: str) -> None:
        """Send SelectPreset command."""
        action = self._action("RC", "SelectPreset")
        if not action:
            raise UpnpError("Missing action RC/SelectPreset")
        await action.async_call(InstanceID=0, PresetName=preset_name)

    # endregion

    # region AVT/Transport actions
    @property
    def has_pause(self) -> bool:
        """Check if device has Pause controls."""
        return self._action("AVT", "Pause") is not None

    @property
    def can_pause(self) -> bool:
        """Check if the device can currently Pause."""
        return self.has_pause and self._can_transport_action("pause")

    async def async_pause(self) -> None:
        """Send pause command."""
        if not self._can_transport_action("pause"):
            _LOGGER.debug("Cannot do Pause")
            return

        action = self._action("AVT", "Pause")
        if not action:
            raise UpnpError("Missing action AVT/Pause")
        await action.async_call(InstanceID=0)

    @property
    def has_play(self) -> bool:
        """Check if device has Play controls."""
        return self._action("AVT", "Play") is not None

    @property
    def can_play(self) -> bool:
        """Check if the device can currently play."""
        return self.has_play and self._can_transport_action("play")

    async def async_play(self) -> None:
        """Send play command."""
        if not self._can_transport_action("play"):
            _LOGGER.debug("Cannot do Play")
            return

        action = self._action("AVT", "Play")
        if not action:
            raise UpnpError("Missing action AVT/Play")
        await action.async_call(InstanceID=0, Speed="1")

    @property
    def can_stop(self) -> bool:
        """Check if the device can currently stop."""
        return self.has_stop and self._can_transport_action("stop")

    @property
    def has_stop(self) -> bool:
        """Check if device has Play controls."""
        return self._action("AVT", "Stop") is not None

    async def async_stop(self) -> None:
        """Send stop command."""
        if not self._can_transport_action("stop"):
            _LOGGER.debug("Cannot do Stop")
            return

        action = self._action("AVT", "Stop")
        if not action:
            raise UpnpError("Missing action AVT/Stop")
        await action.async_call(InstanceID=0)

    @property
    def has_previous(self) -> bool:
        """Check if device has Previous controls."""
        return self._action("AVT", "Previous") is not None

    @property
    def can_previous(self) -> bool:
        """Check if the device can currently Previous."""
        return self.has_previous and self._can_transport_action("previous")

    async def async_previous(self) -> None:
        """Send previous track command."""
        if not self._can_transport_action("previous"):
            _LOGGER.debug("Cannot do Previous")
            return

        action = self._action("AVT", "Previous")
        if not action:
            raise UpnpError("Missing action AVT/Previous")
        await action.async_call(InstanceID=0)

    @property
    def has_next(self) -> bool:
        """Check if device has Next controls."""
        return self._action("AVT", "Next") is not None

    @property
    def can_next(self) -> bool:
        """Check if the device can currently Next."""
        return self.has_next and self._can_transport_action("next")

    async def async_next(self) -> None:
        """Send next track command."""
        if not self._can_transport_action("next"):
            _LOGGER.debug("Cannot do Next")
            return

        action = self._action("AVT", "Next")
        if not action:
            raise UpnpError("Missing action AVT/Next")
        await action.async_call(InstanceID=0)

    def _has_seek_with_mode(self, mode: str) -> bool:
        """Check if device has Seek mode."""
        action = self._action("AVT", "Seek")
        state_var = self._state_variable("AVT", "A_ARG_TYPE_SeekMode")
        if action is None or state_var is None:
            return False
        return mode.lower() in state_var.normalized_allowed_values

    @property
    def has_seek_abs_time(self) -> bool:
        """Check if device has Seek controls, by ABS_TIME."""
        return self._has_seek_with_mode("ABS_TIME")

    @property
    def can_seek_abs_time(self) -> bool:
        """Check if the device can currently Seek with ABS_TIME."""
        return self.has_seek_abs_time and self._can_transport_action("seek")

    async def async_seek_abs_time(self, time: timedelta) -> None:
        """Send seek command with ABS_TIME."""
        if not self._can_transport_action("seek"):
            _LOGGER.debug("Cannot do Seek by ABS_TIME")
            return

        action = self._action("AVT", "Seek")
        if not action:
            raise UpnpError("Missing action AVT/Seek")
        target = time_to_str(time)
        await action.async_call(InstanceID=0, Unit="ABS_TIME", Target=target)

    @property
    def has_seek_rel_time(self) -> bool:
        """Check if device has Seek controls, by REL_TIME."""
        return self._has_seek_with_mode("REL_TIME")

    @property
    def can_seek_rel_time(self) -> bool:
        """Check if the device can currently Seek with REL_TIME."""
        return self.has_seek_rel_time and self._can_transport_action("seek")

    async def async_seek_rel_time(self, time: timedelta) -> None:
        """Send seek command with REL_TIME."""
        if not self._can_transport_action("seek"):
            _LOGGER.debug("Cannot do Seek by REL_TIME")
            return

        action = self._action("AVT", "Seek")
        if not action:
            raise UpnpError("Missing action AVT/Seek")
        target = time_to_str(time)
        await action.async_call(InstanceID=0, Unit="REL_TIME", Target=target)

    @property
    def has_play_media(self) -> bool:
        """Check if device has Play controls."""
        return self._action("AVT", "SetAVTransportURI") is not None

    @property
    def current_track_uri(self) -> Optional[str]:
        """Return the URI of the currently playing track."""
        state_var = self._state_variable("AVT", "CurrentTrackURI")
        if state_var is None:
            _LOGGER.debug("Missing StateVariable AVT/CurrentTrackURI")
            return None

        return state_var.value

    @property
    def av_transport_uri(self) -> Optional[str]:
        """Return the URI of the currently playing resource (playlist or track)."""
        state_var = self._state_variable("AVT", "AVTransportURI")
        if state_var is None:
            _LOGGER.debug("Missing StateVariable AVT/AVTransportURI")
            return None

        return state_var.value

    async def async_set_transport_uri(
        self,
        media_url: str,
        media_title: str,
        meta_data: Union[None, str, Mapping] = None,
    ) -> None:
        """Play a piece of media."""
        # escape media_url
        _LOGGER.debug("Set transport uri: %s", media_url)

        # queue media
        if not isinstance(meta_data, str):
            meta_data = await self.construct_play_media_metadata(
                media_url, media_title, meta_data=meta_data
            )
        action = self._action("AVT", "SetAVTransportURI")
        if not action:
            raise UpnpError("Missing action AVT/SetAVTransportURI")
        await action.async_call(
            InstanceID=0, CurrentURI=media_url, CurrentURIMetaData=meta_data
        )

    @property
    def has_next_transport_uri(self) -> bool:
        """Check if device has controls to set the next item for playback."""
        return (
            self._state_variable("AVT", "NextAVTransportURI") is not None
            and self._action("AVT", "SetNextAVTransportURI") is not None
        )

    async def async_set_next_transport_uri(
        self,
        media_url: str,
        media_title: str,
        meta_data: Union[None, str, Mapping] = None,
    ) -> None:
        """Enqueue a piece of media for playing immediately after the current media."""
        # escape media_url
        _LOGGER.debug("Set next transport uri: %s", media_url)

        # queue media
        if not isinstance(meta_data, str):
            meta_data = await self.construct_play_media_metadata(
                media_url, media_title, meta_data=meta_data
            )
        action = self._action("AVT", "SetNextAVTransportURI")
        if not action:
            raise UpnpError("Missing action AVT/SetNextAVTransportURI")
        await action.async_call(
            InstanceID=0, NextURI=media_url, NextURIMetaData=meta_data
        )

    async def async_wait_for_can_play(self, max_wait_time: float = 5) -> None:
        """Wait for play command to be ready."""
        loop_time = 0.25
        end_time = monotonic_timer() + max_wait_time

        while monotonic_timer() <= end_time:
            if self._can_transport_action("play"):
                break
            await asyncio.sleep(loop_time)
            # Check again before trying to poll, in case variable change event received
            if self._can_transport_action("play"):
                break
            # Poll current transport actions, even if we're subscribed, just in
            # case the device isn't eventing properly.
            await self._async_poll_state_variables(
                "AVT", "GetCurrentTransportActions", InstanceID=0
            )
        else:
            _LOGGER.debug("break out of waiting game")

    async def _fetch_headers(
        self, url: str, headers: Mapping[str, str]
    ) -> Optional[Mapping[str, str]]:
        """Do a HEAD/GET to get resources headers."""
        requester = self.profile_device.requester

        # try a HEAD first
        request = HttpRequest("HEAD", url, headers, None)
        response = await requester.async_http_request(request)
        if 200 <= response.status_code < 300:
            return response.headers

        if response.status_code == HTTPStatus.NOT_FOUND:
            # Give up when the item doesn't exist, otherwise try GET below
            return None

        # then try a GET request for only the first byte of content
        get_headers = dict(headers)
        get_headers["Range"] = "bytes=0-0"
        request = HttpRequest("GET", url, get_headers, None)
        response = await requester.async_http_request(request)
        if 200 <= response.status_code < 300:
            return response.headers

        # finally try a plain GET, which might return a lot of data
        request = HttpRequest("GET", url, headers, None)
        response = await requester.async_http_request(request)
        if 200 <= response.status_code < 300:
            return response.headers

        return None

    async def construct_play_media_metadata(
        self,
        media_url: str,
        media_title: str,
        default_mime_type: Optional[str] = None,
        default_upnp_class: Optional[str] = None,
        override_mime_type: Optional[str] = None,
        override_upnp_class: Optional[str] = None,
        override_dlna_features: Optional[str] = None,
        meta_data: Optional[Mapping[str, Any]] = None,
    ) -> str:
        """
        Construct the metadata for play_media command.

        This queries the source and takes mime_type/dlna_features from it.

        The base metadata is updated with key:values from meta_data, e.g.
        `meta_data = {"artist": "Singer X"}`
        """
        # pylint: disable=too-many-arguments, too-many-locals, too-many-branches
        mime_type = override_mime_type or ""
        upnp_class = override_upnp_class or ""
        dlna_features = override_dlna_features or "*"
        meta_data = meta_data or {}

        if None in (override_mime_type, override_dlna_features):
            # do a HEAD/GET, to retrieve content-type/mime-type
            try:
                headers = await self._fetch_headers(
                    media_url, {"GetContentFeatures.dlna.org": "1"}
                )
                if headers:
                    if not override_mime_type and "Content-Type" in headers:
                        mime_type = headers["Content-Type"]
                    if (
                        not override_dlna_features
                        and "ContentFeatures.dlna.org" in headers
                    ):
                        dlna_features = headers["ContentFeatures.dlna.org"]
            except Exception:  # pylint: disable=broad-except
                pass

            if not mime_type:
                _type = guess_type(media_url.split("?")[0])
                mime_type = _type[0] or ""
                if not mime_type:
                    mime_type = default_mime_type or "application/octet-stream"

            # use CM/GetProtocolInfo to improve on dlna_features
            if (
                not override_dlna_features
                and dlna_features != "*"
                and self.has_get_protocol_info
            ):
                protocol_info_entries = (
                    await self._async_get_sink_protocol_info_for_mime_type(mime_type)
                )
                for entry in protocol_info_entries:
                    if entry[3] == "*":
                        # device accepts anything, send this
                        dlna_features = "*"

        # Try to derive a basic upnp_class from mime_type
        if not override_upnp_class:
            mime_type = mime_type.lower()
            for _mime, _class in MIME_TO_UPNP_CLASS_MAPPING.items():
                if mime_type.startswith(_mime):
                    upnp_class = _class
                    break
            else:
                upnp_class = default_upnp_class or "object.item"

        # build DIDL-Lite item + resource
        didl_item_type = didl_lite.type_by_upnp_class(upnp_class)
        if not didl_item_type:
            raise UpnpError("Unknown DIDL-lite type")

        protocol_info = f"http-get:*:{mime_type}:{dlna_features}"
        resource = didl_lite.Resource(uri=media_url, protocol_info=protocol_info)
        item = didl_item_type(
            id="0",
            parent_id="-1",
            title=media_title or meta_data.get("title"),
            restricted="false",
            resources=[resource],
        )

        # Set any metadata properties that are supported by the DIDL item
        for key, value in meta_data.items():
            setattr(item, key, str(value))

        xml_string: bytes = didl_lite.to_xml_string(item)
        return xml_string.decode("utf-8")

    async def _async_get_sink_protocol_info_for_mime_type(
        self, mime_type: str
    ) -> List[List[str]]:
        """Get protocol_info for a specific mime type."""
        # example entry:
        # http-get:*:video/mpeg:DLNA.ORG_PN=MPEG_TS_HD_KO_ISO;DLNA.ORG_FLAGS=ED100000000000000000...
        return [
            entry.split(":")
            for entry in self.source_protocol_info
            if ":" in entry and entry.split(":")[2] == mime_type
        ]

    # endregion

    # region: AVT/PlayMode
    @property
    def has_play_mode(self) -> bool:
        """Check if device supports setting the play mode."""
        return (
            self._state_variable("AVT", "CurrentPlayMode") is not None
            and self._action("AVT", "SetPlayMode") is not None
        )

    @property
    def valid_play_modes(self) -> Set[PlayMode]:
        """Return a set of play modes that can be used."""
        play_modes: Set[PlayMode] = set()
        state_var = self._state_variable("AVT", "CurrentPlayMode")
        if state_var is None:
            return play_modes

        for normalized_allowed_value in state_var.normalized_allowed_values:
            try:
                mode = PlayMode[normalized_allowed_value.upper()]
            except KeyError:
                # Unknown mode, don't report it as valid
                continue
            play_modes.add(mode)

        return play_modes

    @property
    def play_mode(self) -> Optional[PlayMode]:
        """Get play mode."""
        state_var = self._state_variable("AVT", "CurrentPlayMode")
        if not state_var:
            return None

        state_value = (state_var.value or "").strip().upper()
        try:
            return PlayMode[state_value]
        except KeyError:
            # Unknown mode; return VENDOR_DEFINED.
            return PlayMode.VENDOR_DEFINED

    async def async_set_play_mode(self, mode: PlayMode) -> None:
        """Send SetPlayMode command."""
        action = self._action("AVT", "SetPlayMode")
        if not action:
            raise UpnpError("Missing action AVT/SetPlayMode")
        await action.async_call(InstanceID=0, NewPlayMode=mode.name)

    # endregion

    # region AVT/Media info
    def _update_current_track_meta_data(self, state_var: UpnpStateVariable) -> None:
        """Update the cached parsed value of AVT/CurrentTrackMetaData."""
        xml = state_var.value
        if not xml or xml == "NOT_IMPLEMENTED":
            self._current_track_meta_data = None
            return

        items = _cached_from_xml_string(xml)
        if not items:
            self._current_track_meta_data = None
            return

        item = items[0]
        if not isinstance(item, didl_lite.DidlObject):
            self._current_track_meta_data = None
            return

        self._current_track_meta_data = item

    def _get_current_track_meta_data(self, attr: str) -> Optional[str]:
        """Return a metadata attribute if it exists, None otherwise."""
        if not self._current_track_meta_data:
            return None

        if not hasattr(self._current_track_meta_data, attr):
            return None

        value: str = getattr(self._current_track_meta_data, attr)
        return value

    @property
    def media_class(self) -> Optional[str]:
        """DIDL-Lite class of currently playing media."""
        if not self._current_track_meta_data:
            return None
        media_class: str = self._current_track_meta_data.upnp_class
        return media_class

    @property
    def media_title(self) -> Optional[str]:
        """Title of current playing media."""
        return self._get_current_track_meta_data("title")

    @property
    def media_program_title(self) -> Optional[str]:
        """Title of current playing media."""
        return self._get_current_track_meta_data("program_title")

    @property
    def media_artist(self) -> Optional[str]:
        """Artist of current playing media."""
        return self._get_current_track_meta_data("artist")

    @property
    def media_album_name(self) -> Optional[str]:
        """Album name of current playing media."""
        return self._get_current_track_meta_data("album")

    @property
    def media_album_artist(self) -> Optional[str]:
        """Album artist of current playing media."""
        return self._get_current_track_meta_data("album_artist")

    @property
    def media_track_number(self) -> Optional[int]:
        """Track number of current playing media."""
        state_var = self._state_variable("AVT", "CurrentTrack")
        if state_var is None:
            _LOGGER.debug("Missing StateVariable AVT/CurrentTrack")
            return None

        value: Optional[int] = state_var.value
        return value

    @property
    def media_series_title(self) -> Optional[str]:
        """Title of series of currently playing media."""
        return self._get_current_track_meta_data("series_title")

    @property
    def media_season_number(self) -> Optional[str]:
        """Season of series of currently playing media."""
        return self._get_current_track_meta_data("episode_season")

    @property
    def media_episode_number(self) -> Optional[str]:
        """Episode number, within the series, of current playing media.

        Note: This is usually the absolute number, starting at 1, of the episode
        within the *series* and not the *season*.
        """
        return self._get_current_track_meta_data("episode_number")

    @property
    def media_episode_count(self) -> Optional[str]:
        """Total number of episodes in series to which currently playing media belongs."""
        return self._get_current_track_meta_data("episode_count")

    @property
    def media_channel_name(self) -> Optional[str]:
        """Name of currently playing channel."""
        return self._get_current_track_meta_data("channel_name")

    @property
    def media_channel_number(self) -> Optional[str]:
        """Channel number of currently playing channel."""
        return self._get_current_track_meta_data("channel_number")

    @property
    def media_image_url(self) -> Optional[str]:
        """Image url of current playing media."""
        state_var = self._state_variable("AVT", "CurrentTrackMetaData")
        if state_var is None:
            return None

        xml = state_var.value
        if not xml or xml == "NOT_IMPLEMENTED":
            return None

        items = _cached_from_xml_string(xml)
        if not items:
            return None

        device_url = self.profile_device.device_url
        for item in items:
            # Some players use Item.albumArtURI,
            # though not found in the UPnP-av-ConnectionManager-v1-Service spec.
            if hasattr(item, "album_art_uri") and item.album_art_uri is not None:
                return absolute_url(device_url, item.album_art_uri)

            for res in item.resources:
                protocol_info = res.protocol_info or ""
                if protocol_info.startswith("http-get:*:image/"):
                    return absolute_url(device_url, res.url)

        return None

    @property
    def media_duration(self) -> Optional[int]:
        """Duration of current playing media in seconds."""
        state_var = self._state_variable("AVT", "CurrentTrackDuration")
        if (
            state_var is None
            or state_var.value is None
            or state_var.value == "NOT_IMPLEMENTED"
        ):
            return None

        time = str_to_time(state_var.value)
        if time is None:
            return None

        return time.seconds

    @property
    def media_position(self) -> Optional[int]:
        """Position of current playing media in seconds."""
        state_var = self._state_variable("AVT", "RelativeTimePosition")
        if (
            state_var is None
            or state_var.value is None
            or state_var.value == "NOT_IMPLEMENTED"
        ):
            return None

        time = str_to_time(state_var.value)
        if time is None:
            return None

        return time.seconds

    @property
    def media_position_updated_at(self) -> Optional[datetime]:
        """When was the position of the current playing media valid."""
        state_var = self._state_variable("AVT", "RelativeTimePosition")
        if state_var is None:
            return None

        return state_var.updated_at

    # endregion

    # region AVT/Playlist info
    def _update_av_transport_uri_metadata(self, state_var: UpnpStateVariable) -> None:
        """Update the cached parsed value of AVT/AVTransportURIMetaData."""
        xml = state_var.value
        if not xml or xml == "NOT_IMPLEMENTED":
            self._av_transport_uri_meta_data = None
            return

        items = _cached_from_xml_string(xml)
        if not items:
            self._av_transport_uri_meta_data = None
            return

        item = items[0]
        if not isinstance(item, didl_lite.DidlObject):
            self._av_transport_uri_meta_data = None
            return

        self._av_transport_uri_meta_data = item

    def _get_av_transport_meta_data(self, attr: str) -> Optional[str]:
        """Return an attribute of AVTransportURIMetaData if it exists, None otherwise."""
        if not self._av_transport_uri_meta_data:
            return None

        if not hasattr(self._av_transport_uri_meta_data, attr):
            return None

        value: str = getattr(self._av_transport_uri_meta_data, attr)
        return value

    @property
    def media_playlist_title(self) -> Optional[str]:
        """Title of currently playing playlist, if a playlist is playing."""
        if self.av_transport_uri == self.current_track_uri:
            # A single track is playing, no playlist to report
            return None

        return self._get_av_transport_meta_data("title")

    # endregion


class DmsDevice(ConnectionManagerMixin, UpnpProfileDevice):
    """Representation of a DLNA DMS device."""

    DEVICE_TYPES = [
        "urn:schemas-upnp-org:device:MediaServer:1",
        "urn:schemas-upnp-org:device:MediaServer:2",
        "urn:schemas-upnp-org:device:MediaServer:3",
        "urn:schemas-upnp-org:device:MediaServer:4",
    ]

    SERVICE_IDS = frozenset(
        (
            "urn:upnp-org:serviceId:ConnectionManager",
            "urn:upnp-org:serviceId:ContentDirectory",
        )
    )

    _SERVICE_TYPES = {
        "CD": {
            "urn:schemas-upnp-org:service:ContentDirectory:4",
            "urn:schemas-upnp-org:service:ContentDirectory:3",
            "urn:schemas-upnp-org:service:ContentDirectory:2",
            "urn:schemas-upnp-org:service:ContentDirectory:1",
        },
        **ConnectionManagerMixin._SERVICE_TYPES,
    }

    METADATA_FILTER_ALL = "*"
    DEFAULT_METADATA_FILTER = METADATA_FILTER_ALL
    DEFAULT_SORT_CRITERIA = ""

    __did_first_update: bool = False

    async def async_update(self, do_ping: bool = False) -> None:
        """Retrieve the latest data."""
        # pylint: disable=arguments-differ
        await super().async_update()

        # Retrieve unevented changeable values
        if not self.is_subscribed or not self.__did_first_update:
            await self._async_poll_state_variables("CD", "GetSystemUpdateID")
        elif do_ping:
            await self.profile_device.async_ping()

        # Retrieve unchanging state variables only once
        if not self.__did_first_update:
            await self._async_poll_state_variables(
                "CD", ["GetSearchCapabilities", "GetSortCapabilities"]
            )
            self.__did_first_update = True

    def get_absolute_url(self, url: str) -> str:
        """Resolve a URL returned by the device into an absolute URL."""
        return absolute_url(self.device.device_url, url)

    # region CD
    @property
    def search_capabilities(self) -> List[str]:
        """List of capabilities that are supported for search."""
        state_var = self._state_variable("CD", "SearchCapabilities")
        if state_var is None or state_var.value is None:
            return []

        return split_commas(state_var.value)

    @property
    def sort_capabilities(self) -> List[str]:
        """List of meta-data tags that can be used in sort_criteria."""
        state_var = self._state_variable("CD", "SortCapabilities")
        if state_var is None or state_var.value is None:
            return []

        return split_commas(state_var.value)

    @property
    def system_update_id(self) -> Optional[int]:
        """Return the latest update SystemUpdateID.

        Changes to this ID indicate that changes have occurred in the Content
        Directory.
        """
        state_var = self._state_variable("CD", "SystemUpdateID")
        if state_var is None or state_var.value is None:
            return None

        return int(state_var.value)

    @property
    def has_container_update_ids(self) -> bool:
        """Check if device supports the ContainerUpdateIDs variable."""
        return self._action("CD", "ContainerUpdateIDs") is not None

    @property
    def container_update_ids(self) -> Optional[Dict[str, int]]:
        """Return latest list of changed containers.

        This variable is evented only, and optional. If it's None, use the
        system_update_id to track container changes instead.

        :return: Mapping of container IDs to container update IDs
        """
        state_var = self._state_variable("CD", "ContainerUpdateIDs")
        if state_var is None or state_var.value is None:
            return None

        # Convert list of containerID,updateID,containerID,updateID pairs to dict
        id_list = split_commas(state_var.value)
        return {id_list[i]: int(id_list[i + 1]) for i in range(0, len(id_list), 2)}

    class BrowseResult(NamedTuple):
        """Result returned from a Browse or Search action."""

        result: List[Union[didl_lite.DidlObject, didl_lite.Descriptor]]
        number_returned: int
        total_matches: int
        update_id: int

    async def async_browse(
        self,
        object_id: str,
        browse_flag: str,
        metadata_filter: Union[Iterable[str], str] = DEFAULT_METADATA_FILTER,
        starting_index: int = 0,
        requested_count: int = 0,
        sort_criteria: Union[Iterable[str], str] = DEFAULT_SORT_CRITERIA,
    ) -> BrowseResult:
        """Retrieve an object's metadata or its children."""
        # pylint: disable=too-many-arguments
        action = self._action("CD", "Browse")
        if not action:
            raise UpnpError("Missing action CD/Browse")

        if not isinstance(metadata_filter, str):
            metadata_filter = ",".join(metadata_filter)

        if not isinstance(sort_criteria, str):
            sort_criteria = ",".join(sort_criteria)

        result = await action.async_call(
            ObjectID=object_id,
            BrowseFlag=browse_flag,
            Filter=metadata_filter,
            StartingIndex=starting_index,
            RequestedCount=requested_count,
            SortCriteria=sort_criteria,
        )

        return DmsDevice.BrowseResult(
            didl_lite.from_xml_string(result["Result"], strict=False),
            int(result["NumberReturned"]),
            int(result["TotalMatches"]),
            int(result["UpdateID"]),
        )

    async def async_browse_metadata(
        self,
        object_id: str,
        metadata_filter: Union[Iterable[str], str] = DEFAULT_METADATA_FILTER,
    ) -> didl_lite.DidlObject:
        """Get the metadata (properties) of an object."""
        _LOGGER.debug("browse_metadata(%r, %r)", object_id, metadata_filter)
        result = await self.async_browse(
            object_id,
            "BrowseMetadata",
            metadata_filter,
        )
        metadata = result.result[0]
        assert isinstance(metadata, didl_lite.DidlObject)
        _LOGGER.debug("browse_metadata -> %r", metadata)
        return metadata

    async def async_browse_direct_children(
        self,
        object_id: str,
        metadata_filter: Union[Iterable[str], str] = DEFAULT_METADATA_FILTER,
        starting_index: int = 0,
        requested_count: int = 0,
        sort_criteria: Union[Iterable[str], str] = DEFAULT_SORT_CRITERIA,
    ) -> BrowseResult:
        """Get the direct children of an object."""
        # pylint: disable=too-many-arguments
        _LOGGER.debug("browse_direct_children(%r, %r)", object_id, metadata_filter)
        result = await self.async_browse(
            object_id,
            "BrowseDirectChildren",
            metadata_filter,
            starting_index,
            requested_count,
            sort_criteria,
        )
        _LOGGER.debug("browse_direct_children -> %r", result)
        return result

    @property
    def has_search_directory(self) -> bool:
        """Check if device supports the Search action."""
        return self._action("CD", "Search") is not None

    async def async_search_directory(
        self,
        container_id: str,
        search_criteria: str,
        metadata_filter: Union[Iterable[str], str] = DEFAULT_METADATA_FILTER,
        starting_index: int = 0,
        requested_count: int = 0,
        sort_criteria: Union[Iterable[str], str] = DEFAULT_SORT_CRITERIA,
    ) -> BrowseResult:
        """Search ContentDirectory for objects that match some criteria.

        NOTE: This is not UpnpProfileDevice.async_search, which searches for
        matching UPnP devices.
        """
        # pylint: disable=too-many-arguments
        _LOGGER.debug(
            "search_directory(%r, %r, %r)",
            container_id,
            search_criteria,
            metadata_filter,
        )

        action = self._action("CD", "Search")
        if not action:
            raise UpnpError("Missing action CD/Search")

        if not isinstance(metadata_filter, str):
            metadata_filter = ",".join(metadata_filter)
        if not isinstance(sort_criteria, str):
            sort_criteria = ",".join(sort_criteria)

        result = await action.async_call(
            ContainerID=container_id,
            SearchCriteria=search_criteria,
            Filter=metadata_filter,
            StartingIndex=starting_index,
            RequestedCount=requested_count,
            SortCriteria=sort_criteria,
        )

        browse_result = DmsDevice.BrowseResult(
            didl_lite.from_xml_string(result["Result"], strict=False),
            int(result["NumberReturned"]),
            int(result["TotalMatches"]),
            int(result["UpdateID"]),
        )

        _LOGGER.debug("search_directory -> %r", browse_result)

        return browse_result

    # endregion


class ContentDirectoryErrorCode(IntEnum):
    """Error codes specific to DLNA Content Directory actions."""

    NO_SUCH_OBJECT = 701
    INVALID_CURRENT_TAG_VALUE = 702
    INVALID_NEW_TAG_VALUE = 703
    REQUIRED_TAG = 704
    READ_ONLY_TAG = 705
    PARAMETER_MISMATCH = 706
    INVALID_SEARCH_CRITERIA = 708
    INVALID_SORT_CRITERIA = 709
    NO_SUCH_CONTAINER = 710
    RESTRICTED_OJECT = 711
    BAD_METADATA = 712
    RESTRICTED_PARENT_OBJECT = 713
    NO_SUCH_SOURCE_RESOURCES = 714
    SOURCE_RESOURCE_ACCESS_DENIED = 715
    TRANSFER_BUSY = 716
    NO_SUCH_FILE_TRANSFER = 717
    NO_SUCH_DESTINATION_SOURCE = 718
    DESTINATION_RESOURCE_ACCESS_DENIED = 719
    CANNOT_PROCESS_REQUEST = 720
