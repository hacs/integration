'''
Disk quota events monitoring:

.. testsetup::

    from pyroute2.netlink.event import dquot
    import pyroute2
    pyroute2.DQuotSocket = dquot.DQuotMock

.. testcode::

    from pyroute2 import DQuotSocket

    with DQuotSocket() as ds:
        for message in ds.get():
            uid = message.get('QUOTA_NL_A_EXCESS_ID')
            major = message.get('QUOTA_NL_A_DEV_MAJOR')
            minor = message.get('QUOTA_NL_A_DEV_MINOR')
            warning = message.get('QUOTA_NL_A_WARNING')
            print(f'quota warning {warning} for uid {uid} on {major}:{minor}')

.. testoutput::

    quota warning 8 for uid 0 on 7:0
'''

from pyroute2.common import load_dump
from pyroute2.netlink import genlmsg
from pyroute2.netlink.event import EventSocket
from pyroute2.netlink.nlsocket import Marshal

QUOTA_NL_C_UNSPEC = 0
QUOTA_NL_C_WARNING = 1


class dquotmsg(genlmsg):
    prefix = 'QUOTA_NL_A_'
    nla_map = (
        ('QUOTA_NL_A_UNSPEC', 'none'),
        ('QUOTA_NL_A_QTYPE', 'uint32'),
        ('QUOTA_NL_A_EXCESS_ID', 'uint64'),
        ('QUOTA_NL_A_WARNING', 'uint32'),
        ('QUOTA_NL_A_DEV_MAJOR', 'uint32'),
        ('QUOTA_NL_A_DEV_MINOR', 'uint32'),
        ('QUOTA_NL_A_CAUSED_ID', 'uint64'),
        ('QUOTA_NL_A_PAD', 'uint64'),
    )


class MarshalDQuot(Marshal):
    msg_map = {QUOTA_NL_C_UNSPEC: dquotmsg, QUOTA_NL_C_WARNING: dquotmsg}


class DQuotSocket(EventSocket):
    marshal_class = MarshalDQuot
    genl_family = 'VFS_DQUOT'


class DQuotMock(DQuotSocket):
    input_from_buffer_queue = True
    sample_data = '''
        4c:00:00:00  11:00:00:00  06:00:00:00  00:00:00:00
        01:01:00:00  08:00:01:00  00:00:00:00  0c:00:02:00
        00:00:00:00  00:00:00:00  08:00:03:00  08:00:00:00
        08:00:04:00  07:00:00:00  08:00:05:00  00:00:00:00
        0c:00:06:00  00:00:00:00  00:00:00:00
    '''

    def bind(self, groups=0, **kwarg):
        self.marshal.msg_map[17] = dquotmsg

    def get(self):
        self.buffer_queue.put(load_dump(self.sample_data))
        return super().get()
