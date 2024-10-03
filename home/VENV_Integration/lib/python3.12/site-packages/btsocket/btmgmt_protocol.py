"""
Hand the BlueZ Bluetooth Management (mgmt) API
"""
import abc
from collections import namedtuple
from enum import Enum
import sys
from btsocket import tools

logger = tools.create_module_logger(__name__)
current_module = sys.modules[__name__]

Parameter = namedtuple('Parameter',
                       ('name', 'width', 'repeat', 'bt_type'),
                       defaults=(1, 'IntUL'))
Response = namedtuple('Response',
                      ('header', 'event_frame', 'cmd_response_frame'),
                      defaults=(None,))
Command = namedtuple('Command', ('header', 'cmd_params_frame'),
                     defaults=(None,))


class DataField(metaclass=abc.ABCMeta):
    def __init__(self):
        self.octets = b''
        self.value = None

    def __repr__(self):
        return f'{self.value}'

    @abc.abstractmethod
    def decode(self, data):
        pass

    @abc.abstractmethod
    def encode(self, value, width):
        pass


class Address(DataField):
    def decode(self, data):
        self.value = (f'{data[5]:02X}:{data[4]:02X}:{data[3]:02X}:'
                      f'{data[2]:02X}:{data[1]:02X}:{data[0]:02X}')
        self.octets = data

    def encode(self, value, width):
        parts = value.split(':')
        for idx in range(5, -1, -1):
            self.octets += int(parts[idx], 16).to_bytes(1, byteorder='little')
        self.value = value


class AddressTypeField(DataField):
    def decode(self, data):
        addr_types = []
        as_int = int.from_bytes(data, byteorder='little', signed=False)
        for i in range(len(AddressType)):
            if (as_int >> i) & 1:
                addr_types.append(AddressType(i))
        self.value = addr_types
        self.octets = data

    def encode(self, value, width):
        self.value = value
        bits = 0
        for i in value:
            bits = bits | (1 << i.value)
        self.octets = int(bits).to_bytes(1, byteorder='little', signed=False)


class IntUL(DataField):

    def decode(self, data):
        self.value = int.from_bytes(data, byteorder='little', signed=False)
        self.octets = data

    def encode(self, value, width):
        self.octets = int(value).to_bytes(width, byteorder='little',
                                          signed=False)
        self.value = value


class HexStr(DataField):

    def decode(self, data):
        self.value = data.hex()
        self.octets = data

    def encode(self, value, width):
        self.octets = bytes.fromhex(value)
        self.value = value


class CmdCode(DataField):

    def decode(self, data):
        self.value = Commands(int.from_bytes(data, byteorder='little'))
        self.octets = data

    def encode(self, value, width):
        cmd_code = Commands[value]
        self.octets = int(cmd_code.value).to_bytes(width, byteorder='little',
                                                   signed=False)
        self.value = cmd_code


class EvtCode(DataField):

    def decode(self, data):
        self.value = Events(int.from_bytes(data, byteorder='little'))
        self.octets = data

    def encode(self, value, width):
        evt_code = Events[value]
        self.octets = int(evt_code.value).to_bytes(width, byteorder='little',
                                                   signed=False)
        self.value = evt_code


class Status(DataField):

    def decode(self, data):
        self.value = ErrorCodes(int.from_bytes(data, byteorder='little'))
        self.octets = data

    def encode(self, value, width):
        status_code = ErrorCodes[value]
        self.octets = int(status_code.value).to_bytes(width,
                                                      byteorder='little',
                                                      signed=False)
        self.value = status_code


class Controller(DataField):

    def decode(self, data):
        self.value = int.from_bytes(data, byteorder='little', signed=False)
        self.octets = data

    def encode(self, value, width):
        if value is None:
            value = 0xffff
        self.octets = int(value).to_bytes(width, byteorder='little',
                                          signed=False)
        self.value = value


class ParamLen(DataField):

    def decode(self, data):
        self.value = int.from_bytes(data, byteorder='little', signed=False)
        self.octets = data

    def encode(self, value, width):
        self.value = value
        try:
            len_bytes = len(value)
        except IndexError:
            len_bytes = 0
        self.octets = len_bytes.to_bytes(width, byteorder='little',
                                         signed=False)


class Name(DataField):

    def decode(self, data):
        self.value = data.rstrip(b'\x00')
        self.octets = data

    def encode(self, value, width):
        self.value = value
        self.octets = value.ljust(width, b'\x00')


class CurrentSettings(DataField):

    def decode(self, data):
        self.value = dict()
        as_int = int.from_bytes(data, byteorder='little', signed=False)
        for i in range(len(SupportedSettings)):
            self.value[SupportedSettings(i)] = bool((as_int >> i) & 1)
        self.octets = data

    def encode(self, value, width):
        raise NotImplementedError


class EIRData(DataField):
    def decode(self, data):
        self.value = dict()
        pointer = 0
        while pointer < len(data):
            len_data = data[pointer]
            data_type = data[pointer + 1]
            data_start = pointer + 2
            data_end = data_start + len_data - 1
            self.value[ADType(data_type)] = data[data_start:data_end]
            pointer += data[pointer] + 1

    def encode(self, value, width):
        raise NotImplementedError


class Packet:
    def __init__(self, shape):
        # e.g.
        # shape = (Parameter('opcode', 2), Parameter('status', 1))
        self.shape = shape
        for param in shape:
            self.__setattr__(param.name, None)
        # params = b'\x01\x00\x00\x01\x0e\x00'
        self.octets = b''

    def __repr__(self):
        key_values = ', '.join([f'{x.name}={self.__getattribute__(x.name)}'
                               for x in self.shape])
        return f'<{key_values}>'

    def _add_to_value(self, param, p_value):
        if param.repeat != 1:
            self.__getattribute__(param.name).append(p_value)
        else:
            self.__setattr__(param.name, p_value)

    def decode(self, pkt):
        self.octets = pkt
        pointer = 0
        for param in self.shape:
            logger.debug('Decoding %s as type %s', param.name, param.bt_type)
            if param.repeat != 1:
                repeated = self.__getattribute__(param.repeat)
                self.__setattr__(param.name, list())
            else:
                repeated = param.repeat
            for index in range(repeated):
                class_ = getattr(current_module, param.bt_type)
                data_type = class_()
                data_type.decode(pkt[pointer:pointer + param.width])
                self._add_to_value(param, data_type.value)
                pointer += param.width
        if pointer < len(pkt):
            # self.value['parameters'] = pkt[pointer:]
            return pkt[pointer:]
        return None

    def encode(self, *args):
        self.octets = b''
        cmd_args = args[0]
        for entry in range(len(self.shape)):
            param = self.shape[entry]
            logger.debug('Encoding %s as type %s', param.name, param.bt_type)
            class_ = getattr(current_module, param.bt_type)
            data_type = class_()
            if param.bt_type == 'ParamLen':
                try:
                    data_type.encode(cmd_args[entry], param.width)
                except IndexError:
                    data_type.encode(b'', param.width)
            else:
                data_type.encode(cmd_args[entry], param.width)
            self.octets += data_type.octets
            self._add_to_value(param, data_type.value)
        return cmd_args[2:]


class EventHeader(Packet):
    def __init__(self):
        super().__init__([Parameter(name='event_code', width=2,
                                    bt_type='EvtCode'),
                          Parameter(name='controller_idx', width=2,
                                    bt_type='Controller'),
                          Parameter(name='param_len', width=2,
                                    bt_type='ParamLen')])


class CmdHeader(Packet):
    def __init__(self):
        super().__init__([Parameter(name='cmd_code', width=2,
                                    bt_type='CmdCode'),
                          Parameter(name='controller_idx', width=2,
                                    bt_type='Controller'),
                          Parameter(name='param_len', width=2,
                                    bt_type='ParamLen')])


class AddressType(Enum):
    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self.name)

    # Possible values for the Address_Type parameter are a bit-wise OR of
    # the following bits
    BREDR = 0x00
    LEPublic = 0x01
    LERandom = 0x02


class SupportedSettings(Enum):
    """
        0	Powered
        1	Connectable
        2	Fast Connectable
        3	Discoverable
        4	Bondable
        5	Link Level Security (Sec. mode 3)
        6	Secure Simple Pairing
        7	Basic Rate/Enhanced Data Rate
        8	High Speed
        9	Low Energy
        10	Advertising
        11	Secure Connections
        12	Debug Keys
        13	Privacy
        14	Controller Configuration
        15	Static Address
        16	PHY Configuration
        17	Wideband Speech

    """
    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self.name)

    Powered = 0x00
    Connectable = 0x01
    FastConnectable = 0x02
    Discoverable = 0x03
    Bondable = 0x04
    LinkLevelSecurity = 0x05
    SecureSimplePairing = 0x06
    BREDR = 0x07
    HighSpeed = 0x08
    LowEnergy = 0x09
    Advertising = 0x0A
    SecureConnections = 0x0B
    DebugKeys = 0x0C
    Privacy = 0x0D
    ControllerConfiguration = 0x0E
    StaticAddress = 0x0F
    PHYConfiguration = 0x10
    WidebandSpeech = 0x11


class ADType(Enum):
    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self.name)

    Flags = 0x01
    IncompleteUUID16ServiceList = 0x02
    CompleteUUID16ServiceList = 0x03
    CompleteUUID32ServiceList = 0x04
    IncompleteUUID32ServiceList = 0x05
    IncompleteUUID128ServiceList = 0x06
    CompleteUUID128ServiceList = 0x07
    ShortName = 0x08
    CompleteName = 0x09
    TXPower = 0x0a
    DeviceClass = 0x0d
    SimplePairingHashC192 = 0x0e
    SimplePairingRandomizer192 = 0x0f
    SecurityManagerTKValue = 0x10
    SecurityManagerOOBFlags = 0x11
    ConnectionIntervalRange = 0x12
    SolicitUUID16ServiceList = 0x14
    SolicitUUID128ServiceList = 0x15
    ServiceDataUUID16 = 0x16
    PublicTargetAddress = 0x17
    RandomTargetAddress = 0x18
    Appearance = 0x19
    AdvertisingInterval = 0x1a
    LEDeviceAddress = 0x1b
    LERole = 0x1c
    SimplePairingHashC256 = 0x1d
    SimplePairingRandomizer256 = 0x1e
    SolicitUUID32ServiceList = 0x1f
    ServiceDataUUID32 = 0x20
    ServiceDataUUID128 = 0x21
    LESecureConnectionsConfirmationValue = 0x22
    LESecureConnectionsRandomValue = 0x23
    URI = 0x24
    IndoorPositioning = 0x25
    TransportDiscoverData = 0x26
    LESupportedFeatures = 0x27
    ChannelMapUpdateIndication = 0x28
    PBADV = 0x29
    MeshMessage = 0x2a
    MeshBeacon = 0x2b
    BIGInfo = 0x2c
    BroadcastCode = 0x2d
    InformationData3d = 0x3d
    ManufacturerData = 0xff


class ErrorCodes(Enum):
    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self.name)

    Success = 0x00
    UnknownCommand = 0x01
    NotConnected = 0x02
    Failed = 0x03
    ConnectFailed = 0x04
    AuthenticationFailed = 0x05
    NotPaired = 0x06
    NoResources = 0x07
    Timeout = 0x08
    AlreadyConnected = 0x09
    Busy = 0x0A
    Rejected = 0x0B
    NotSupported = 0x0C
    InvalidParameters = 0x0D
    Disconnected = 0x0E
    NotPowered = 0x0F
    Cancelled = 0x10
    InvalidIndex = 0x11
    RFKilled = 0x12
    AlreadyPaired = 0x13
    PermissionDenied = 0x14


class Commands(Enum):
    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self.name)

    ReadManagementVersionInformation = 0x0001
    ReadManagementSupportedCommands = 0x0002
    ReadControllerIndexList = 0x0003
    ReadControllerInformation = 0x0004
    SetPowered = 0x0005
    SetDiscoverable = 0x0006
    SetConnectable = 0x0007
    SetFastConnectable = 0x0008
    SetBondable = 0x0009
    SetLinkSecurity = 0x000A
    SetSecureSimplePairing = 0x000B
    SetHighSpeed = 0x000C
    SetLowEnergy = 0x000D
    SetDeviceClass = 0x000E
    SetLocalName = 0x000F
    AddUUID = 0x0010
    RemoveUUID = 0x0011
    LoadLinkKeys = 0x0012
    LoadLongTermKeys = 0x0013
    Disconnect = 0x0014
    GetConnections = 0x0015
    PINCodeReply = 0x0016
    PINCodeNegativeReply = 0x0017
    SetIOCapability = 0x0018
    PairDevice = 0x0019
    CancelPairDevice = 0x001A
    UnpairDevice = 0x001B
    UserConfirmationReply = 0x001C
    UserConfirmationNegativeReply = 0x001D
    UserPasskeyReply = 0x001E
    UserPasskeyNegativeReply = 0x001F
    ReadLocalOutOfBandData = 0x0020
    AddRemoteOutOfBandData = 0x0021
    RemoveRemoteOutOfBandData = 0x0022
    StartDiscovery = 0x0023
    StopDiscovery = 0x0024
    ConfirmName = 0x0025
    BlockDevice = 0x0026
    UnblockDevice = 0x0027
    SetDeviceID = 0x0028
    SetAdvertising = 0x0029
    SetBREDR = 0x002A
    SetStaticAddress = 0x002B
    SetScanParameters = 0x002C
    SetSecureConnections = 0x002D
    SetDebugKeys = 0x002E
    SetPrivacy = 0x002F
    LoadIdentityResolvingKeys = 0x0030
    GetConnectionInformation = 0x0031
    GetClockInformation = 0x0032
    AddDevice = 0x0033
    RemoveDevice = 0x0034
    LoadConnectionParameters = 0x0035
    ReadUnconfiguredControllerIndexList = 0x0036
    ReadControllerConfigurationInformation = 0x0037
    SetExternalConfiguration = 0x0038
    SetPublicAddress = 0x0039
    StartServiceDiscovery = 0x003a
    ReadLocalOutOfBandExtendedData = 0x003b
    ReadExtendedControllerIndexList = 0x003c
    ReadAdvertisingFeatures = 0x003d
    AddAdvertising = 0x003e
    RemoveAdvertising = 0x003f
    GetAdvertisingSizeInformation = 0x0040
    StartLimitedDiscovery = 0x0041
    ReadExtendedControllerInformation = 0x0042
    SetAppearance = 0x0043
    GetPHYConfiguration = 0x0044
    SetPHYConfiguration = 0x0045
    LoadBlockedKeys = 0x0046
    SetWidebandSpeech = 0x0047


class Events(Enum):
    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self.name)

    CommandCompleteEvent = 0x0001
    CommandStatusEvent = 0x0002
    ControllerErrorEvent = 0x0003
    IndexAddedEvent = 0x0004
    IndexRemovedEvent = 0x0005
    NewSettingsEvent = 0x0006
    ClassOfDeviceChangedEvent = 0x0007
    LocalNameChangedEvent = 0x0008
    NewLinkKeyEvent = 0x0009
    NewLongTermKeyEvent = 0x000A
    DeviceConnectedEvent = 0x000B
    DeviceDisconnectedEvent = 0x000C
    ConnectFailedEvent = 0x000D
    PINCodeRequestEvent = 0x000E
    UserConfirmationRequestEvent = 0x000F
    UserPasskeyRequestEvent = 0x0010
    AuthenticationFailedEvent = 0x0011
    DeviceFoundEvent = 0x0012
    DiscoveringEvent = 0x0013
    DeviceBlockedEvent = 0x0014
    DeviceUnblockedEvent = 0x0015
    DeviceUnpairedEvent = 0x0016
    PasskeyNotifyEvent = 0x0017
    NewIdentityResolvingKeyEvent = 0x0018
    NewSignatureResolvingKeyEvent = 0x0019
    DeviceAddedEvent = 0x001a
    DeviceRemovedEvent = 0x001b
    NewConnectionParameterEvent = 0x001c
    UnconfiguredIndexAddedEvent = 0x001d
    UnconfiguredIndexRemovedEvent = 0x001e
    NewConfigurationOptionsEvent = 0x001f
    ExtendedIndexAddedEvent = 0x0020
    ExtendedIndexRemovedEvent = 0x0021
    LocalOutOfBandExtendedDataUpdatedEvent = 0x0022
    AdvertisingAddedEvent = 0x0023
    AdvertisingRemovedEvent = 0x0024
    ExtendedControllerInformationChangedEvent = 0x0025
    PHYConfigurationChangedEvent = 0x0026


cmds = {
    0x0005: Packet([Parameter(name='powered', width=1)]),
    0x0006: Packet([Parameter(name='discoverable', width=1),
                    Parameter(name='timeout', width=2)]),
    0x0007: Packet([Parameter(name='connectable', width=1)]),
    0x0008: Packet([Parameter(name='enable', width=1)]),
    0x0009: Packet([Parameter(name='bondable', width=1)]),
    0x000A: Packet([Parameter(name='link_security', width=1)]),
    0x000B: Packet([Parameter(name='secure_simple_pairing', width=1)]),
    0x000C: Packet([Parameter(name='high_speed', width=1)]),
    0x000D: Packet([Parameter(name='low_energy', width=1)]),
    0x000E: Packet([Parameter(name='major_class', width=1),
                    Parameter(name='minor_class', width=1)]),
    0x000F: Packet([Parameter(name='name', width=249, bt_type='Name'),
                    Parameter(name='short_name', width=11)]),
    0x0010: Packet([Parameter(name='uuid', width=16),
                    Parameter(name='svc_hint', width=1)]),
    0x0011: Packet([Parameter(name='uuid', width=16)]),
    0x0012: Packet([Parameter(name='debug_keys', width=1),
                    Parameter(name='key_count', width=2),
                    Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='key_type', width=1),
                    Parameter(name='value', width=16),
                    Parameter(name='pin_length', width=1)]),
    0x0013: Packet([Parameter(name='key_count', width=2),
                    Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='key_type', width=1),
                    Parameter(name='master', width=1),
                    Parameter(name='encryption_size', width=1),
                    Parameter(name='encryption_diversifier', width=2),
                    Parameter(name='random_number', width=8),
                    Parameter(name='value', width=16)]),
    0x0014: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0016: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='pin_length', width=1),
                    Parameter(name='pin_code', width=16)]),
    0x0017: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0018: Packet([Parameter(name='io_capability', width=1)]),
    0x0019: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='io_capability', width=1)]),
    0x001A: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x001B: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='disconnect', width=1)]),
    0x001C: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x001D: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x001E: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='passkey', width=4)]),
    0x001F: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0021: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='hash_192', width=16),
                    Parameter(name='randomizer_192', width=16),
                    Parameter(name='hash_256', width=16),
                    Parameter(name='randomizer_256', width=16)]),
    0x0022: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0023: Packet([Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0024: Packet([Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0025: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='name_known', width=1)]),
    0x0026: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0027: Packet([Parameter(name='address', width=6),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0028: Packet([Parameter(name='source', width=2),
                    Parameter(name='vendor', width=2),
                    Parameter(name='product', width=2),
                    Parameter(name='version', width=2)]),
    0x0029: Packet([Parameter(name='advertising', width=1)]),
    0x002A: Packet([Parameter(name='br/edr', width=1)]),
    0x002B: Packet([Parameter(name='address', width=6, bt_type='Address')]),
    0x002C: Packet([Parameter(name='interval', width=2),
                    Parameter(name='window', width=2)]),
    0x002D: Packet([Parameter(name='secure_connections', width=1)]),
    0x002E: Packet([Parameter(name='debug_keys', width=1)]),
    0x002F: Packet([Parameter(name='privacy', width=1),
                    Parameter(name='identity_resolving_key', width=16)]),
    0x0030: Packet([Parameter(name='key_count', width=2),
                    Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='value', width=16)]),
    0x0031: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0032: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0033: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='action', width=1)]),
    0x0034: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0035: Packet([Parameter(name='param_count', width=2),
                    Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='min_connection_interval', width=2),
                    Parameter(name='max_connection_interval', width=2),
                    Parameter(name='connection_latency', width=2),
                    Parameter(name='supervision_timeout', width=2)]),
    0x0038: Packet([Parameter(name='configuration', width=1)]),
    0x0039: Packet([Parameter(name='address', width=6, bt_type='Address')]),
    0x003a: Packet([Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='rssi_threshold', width=1),
                    Parameter(name='uuid_count', width=2),
                    Parameter(name='uuid[i]', width=16, repeat='uuid_count')]),
    0x003b: Packet([Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x003e: Packet(
        [
            Parameter(name='instance', width=1),
            Parameter(name='flags', width=4),
            Parameter(name='duration', width=2),
            Parameter(name='timeout', width=2),
            Parameter(name='adv_data_len', width=1),
            Parameter(name='scan_rsp_len', width=1),
            Parameter(
                name='adv_data', width=None, repeat=1, bt_type='HexStr'),
            Parameter(
                name='scan_rsp', width=None, repeat=1, bt_type='HexStr')
        ]
    ),
    0x003f: Packet([Parameter(name='instance', width=1)]),
    0x0040: Packet([Parameter(name='instance', width=1),
                    Parameter(name='flags', width=4)]),
    0x0041: Packet([Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0043: Packet([Parameter(name='appearance', width=2)]),
    0x0045: Packet([Parameter(name='selected_phys', width=4)]),
    0x0046: Packet([Parameter(name='key_count', width=2),
                    Parameter(name='key_type', width=1),
                    Parameter(name='value', width=16)]),
    0x0047: Packet([Parameter(name='wideband_speech', width=1)]),

}

events = {
    0x0001: Packet([Parameter(name='command_opcode', width=2,
                              bt_type='CmdCode'),
                    Parameter(name='status', width=1, bt_type='Status')]),
    0x0002: Packet([Parameter(name='command_opcode', width=2,
                              bt_type='CmdCode'),
                    Parameter(name='status', width=1, bt_type='Status')]),
    0x0003: Packet([Parameter(name='error_code', width=1)]),
    0x0006: Packet([Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings')]),
    0x0007: Packet([Parameter(name='class_of_device', width=3)]),
    0x0008: Packet([Parameter(name='name', width=249, bt_type='Name'),
                    Parameter(name='short_name', width=11)]),
    0x0009: Packet([Parameter(name='store_hint', width=1),
                    Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='key_type', width=1),
                    Parameter(name='value', width=16),
                    Parameter(name='pin_length', width=1)]),
    0x000A: Packet([Parameter(name='store_hint', width=1),
                    Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='key_type', width=1),
                    Parameter(name='master', width=1),
                    Parameter(name='size', width=1),
                    Parameter(name='diversifier', width=2),
                    Parameter(name='number', width=8),
                    Parameter(name='value', width=16)]),
    0x000B: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='flags', width=4),
                    Parameter(name='eir_data_length', width=2),
                    Parameter(name='eir_data', width=65535,
                              bt_type='EIRData')]),
    0x000C: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='reason', width=1)]),
    0x000D: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='status', width=1, bt_type='Status')]),
    0x000E: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='secure', width=1)]),
    0x000F: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='confirm_hint', width=1),
                    Parameter(name='value', width=4)]),
    0x0010: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0011: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='status', width=1, bt_type='Status')]),
    0x0012: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='rssi', width=1),
                    Parameter(name='flags', width=4),
                    Parameter(name='eir_data_length', width=2),
                    Parameter(name='eir_data', width=65535,
                              bt_type='EIRData')]),
    0x0013: Packet([Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='discovering', width=1)]),
    0x0014: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0015: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0016: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0017: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='passkey', width=4),
                    Parameter(name='entered', width=1)]),
    0x0018: Packet([Parameter(name='store_hint', width=1),
                    Parameter(name='random_address', width=6),
                    Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='value', width=16)]),
    0x0019: Packet([Parameter(name='store_hint', width=1),
                    Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='type', width=1),
                    Parameter(name='value', width=16)]),
    0x001a: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='action', width=1)]),
    0x001b: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x001c: Packet([Parameter(name='store_hint', width=1),
                    Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='min_connection_interval', width=2),
                    Parameter(name='max_connection_interval', width=2),
                    Parameter(name='connection_latency', width=2),
                    Parameter(name='supervision_timeout', width=2)]),
    0x001f: Packet([Parameter(name='missing_options', width=4)]),
    0x0020: Packet([Parameter(name='controller_type', width=1),
                    Parameter(name='controller_bus', width=1)]),
    0x0021: Packet([Parameter(name='controller_type', width=1),
                    Parameter(name='controller_bus', width=1)]),
    0x0022: Packet([Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='eir_data_length', width=2),
                    Parameter(name='eir_data', width=65535,
                              bt_type='EIRData')]),
    0x0023: Packet([Parameter(name='instance', width=1)]),
    0x0024: Packet([Parameter(name='instance', width=1)]),
    0x0025: Packet([Parameter(name='eir_data_length', width=2),
                    Parameter(name='eir_data', width=65535,
                              bt_type='EIRData')]),
    0x0026: Packet([Parameter(name='selected_phys', width=4)]),
}

cmd_response = {
    0x0001: Packet([Parameter(name='version', width=1),
                    Parameter(name='revision', width=2)]),
    0x0002: Packet([Parameter(name='num_of_commands', width=2),
                    Parameter(name='num_of_events', width=2),
                    Parameter(name='command', width=2,
                              repeat='num_of_commands'),
                    Parameter(name='event', width=2, repeat='num_of_events')]),
    0x0003: Packet([Parameter(name='num_controllers', width=2),
                    Parameter(name='controller_index[i]', width=2,
                              repeat='num_controllers')]),
    0x0004: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='bluetooth_version', width=1),
                    Parameter(name='manufacturer', width=2),
                    Parameter(name='supported_settings', width=4),
                    Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings'),
                    Parameter(name='class_of_device', width=3),
                    Parameter(name='name', width=249, bt_type='Name'),
                    Parameter(name='short_name', width=11)]),
    0x0005: Packet([Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings')]),
    0x0006: Packet([Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings')]),
    0x0007: Packet([Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings')]),
    0x0008: Packet([Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings')]),
    0x0009: Packet([Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings')]),
    0x000A: Packet([Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings')]),
    0x000B: Packet([Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings')]),
    0x000C: Packet([Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings')]),
    0x000D: Packet([Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings')]),
    0x000E: Packet([Parameter(name='class_of_device', width=3)]),
    0x000F: Packet([Parameter(name='name', width=249, bt_type='Name'),
                    Parameter(name='short_name', width=11)]),
    0x0010: Packet([Parameter(name='class_of_device', width=3)]),
    0x0011: Packet([Parameter(name='class_of_device', width=3)]),
    0x0014: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0015: Packet([Parameter(name='connection_count', width=2),
                    Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0016: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0017: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0019: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x001A: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x001B: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x001C: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x001D: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x001E: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x001F: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0020: Packet([Parameter(name='hash_192', width=16),
                    Parameter(name='randomizer_192', width=16),
                    Parameter(name='hash_256', width=16),
                    Parameter(name='randomizer_256', width=16)]),
    0x0021: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0022: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0023: Packet([Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0024: Packet([Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0025: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0026: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0027: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0029: Packet([Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings')]),
    0x002A: Packet([Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings')]),
    0x002B: Packet([Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings')]),
    0x002D: Packet([Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings')]),
    0x002E: Packet([Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings')]),
    0x002F: Packet([Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings')]),
    0x0031: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='rssi', width=1),
                    Parameter(name='tx_power', width=1),
                    Parameter(name='max_tx_power', width=1)]),
    0x0032: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='local_clock', width=4),
                    Parameter(name='piconet_clock', width=4),
                    Parameter(name='accuracy', width=2)]),
    0x0033: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0034: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0036: Packet([Parameter(name='num_controllers', width=2),
                    Parameter(name='controller_index[i]', width=2)]),
    0x0037: Packet([Parameter(name='manufacturer', width=2),
                    Parameter(name='supported_options', width=4),
                    Parameter(name='missing_options', width=4)]),
    0x0038: Packet([Parameter(name='missing_options', width=4)]),
    0x0039: Packet([Parameter(name='missing_options', width=4)]),
    0x003a: Packet([Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x003b: Packet([Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField'),
                    Parameter(name='eir_data_length', width=2),
                    Parameter(name='eir_data', width=65535,
                              bt_type='EIRData')]),
    0x003c: Packet([Parameter(name='num_controllers', width=2),
                    Parameter(name='controller_index', width=2,
                              repeat='num_controllers'),
                    Parameter(name='controller_type', width=1,
                              repeat='num_controllers'),
                    Parameter(name='controller_bus', width=1,
                              repeat='num_controllers')]),
    0x003d: Packet([Parameter(name='supported_flags', width=4),
                    Parameter(name='max_adv_data_len', width=1),
                    Parameter(name='max_scan_rsp_len', width=1),
                    Parameter(name='max_instances', width=1),
                    Parameter(name='num_instances', width=1),
                    Parameter(name='instance[i]', width=1,
                              repeat='num_instances')]),
    0x003e: Packet([Parameter(name='instance', width=1)]),
    0x003f: Packet([Parameter(name='instance', width=1)]),
    0x0040: Packet([Parameter(name='instance', width=1),
                    Parameter(name='flags', width=4),
                    Parameter(name='max_adv_data_len', width=1),
                    Parameter(name='max_scan_rsp_len', width=1)]),
    0x0041: Packet([Parameter(name='address_type', width=1,
                              bt_type='AddressTypeField')]),
    0x0042: Packet([Parameter(name='address', width=6, bt_type='Address'),
                    Parameter(name='bluetooth_version', width=1),
                    Parameter(name='manufacturer', width=2),
                    Parameter(name='supported_settings', width=4),
                    Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings'),
                    Parameter(name='eir_data_length', width=2),
                    Parameter(name='eir_data', width=65535,
                              bt_type='EIRData')]),
    0x0044: Packet([Parameter(name='supported_phys', width=4),
                    Parameter(name='configurable_phys', width=4),
                    Parameter(name='selected_phys', width=4)]),
    0x0047: Packet([Parameter(name='current_settings', width=4,
                              bt_type='CurrentSettings')]),
}


def reader(pckt):
    # <-  Response packet      ->
    # <- event_header ->|<- event_frame ->
    # <- event_header ->|<- event_frame ->|<- cmd_response_frame ->
    #
    # <- Command Packet    ->
    # <- cmd_header ->|<- cmd_frame ->
    header = EventHeader()
    evt_params = header.decode(pckt)
    event_frame = events.get(header.event_code.value)

    cmd_params = event_frame.decode(evt_params)
    if cmd_params:
        cmd_response_frame = cmd_response.get(event_frame.command_opcode.value)
        cmd_response_frame.decode(cmd_params)
        logger.debug('Socket Read: %s %s %s',
                     header, event_frame, cmd_response_frame)
        return Response(header, event_frame, cmd_response_frame)
    logger.debug('Socket read %s %s', header, event_frame)
    return Response(header, event_frame)


def command(*args):
    header = CmdHeader()
    if len(args) == 2:
        header.encode(args)
        return Command(header)

    cmd_frame = cmds.get(Commands[args[0]].value)
    cmd_frame.encode(args[2:])
    header.encode((args[0], args[1], cmd_frame.octets))
    return Command(header, cmd_frame)
