'''
Monitor and receive ACPI events messages via generic netlink.

.. testsetup::

    from pyroute2.netlink.event import acpi_event
    import pyroute2
    pyroute2.AcpiEventSocket = acpi_event.AcpiEventMock

.. testcode::

    from pprint import pprint
    from pyroute2 import AcpiEventSocket

    acpi = AcpiEventSocket()
    for message in acpi.get():
        pprint(message.get('ACPI_GENL_ATTR_EVENT'))

.. testoutput::

    {'bus_id': b'LEN0268:00',
     'data': 1251328,
     'device_class': b'ibm/hotkey',
     'type': 32768}

'''

from pyroute2.common import load_dump
from pyroute2.netlink import genlmsg, nla
from pyroute2.netlink.event import EventSocket
from pyroute2.netlink.nlsocket import Marshal

ACPI_GENL_CMD_UNSPEC = 0
ACPI_GENL_CMD_EVENT = 1


class acpimsg(genlmsg):
    nla_map = (
        ('ACPI_GENL_ATTR_UNSPEC', 'none'),
        ('ACPI_GENL_ATTR_EVENT', 'acpiev'),
    )

    class acpiev(nla):
        fields = (
            ('device_class', '20s'),
            ('bus_id', '15s'),
            ('type', 'I'),
            ('data', 'I'),
        )

        def decode(self):
            nla.decode(self)
            dc = self['device_class']
            bi = self['bus_id']
            self['device_class'] = dc[: dc.find(b'\x00')]
            self['bus_id'] = bi[: bi.find(b'\x00')]


class MarshalAcpiEvent(Marshal):
    msg_map = {ACPI_GENL_CMD_UNSPEC: acpimsg, ACPI_GENL_CMD_EVENT: acpimsg}


class AcpiEventSocket(EventSocket):
    marshal_class = MarshalAcpiEvent
    genl_family = 'acpi_event'


class AcpiEventMock(AcpiEventSocket):
    input_from_buffer_queue = True
    sample_data = '''
        44:00:00:00  1b:00:00:00  9b:8b:00:00  00:00:00:00
        01:01:00:00  30:00:01:00  69:62:6d:2f  68:6f:74:6b
        65:79:00:00  00:00:00:00  00:00:00:00  4c:45:4e:30
        32:36:38:3a  30:30:00:00  00:00:00:00  80:00:00:00
        18:13:00:00
    '''

    def bind(self, groups=0, **kwarg):
        self.marshal.msg_map[27] = acpimsg

    def get(self):
        self.buffer_queue.put(load_dump(self.sample_data))
        return super().get()
