from pyroute2.netlink import NETLINK_KOBJECT_UEVENT, nlmsg
from pyroute2.netlink.nlsocket import Marshal, NetlinkSocket


class ueventmsg(nlmsg):
    pass


class MarshalUevent(Marshal):
    def parse(self, data, seq=None, callback=None):
        ret = ueventmsg()
        ret['header']['sequence_number'] = 0
        data = data.split(b'\x00')
        wtf = []
        ret['header']['message'] = data[0].decode('utf-8')
        ret['header']['unparsed'] = b''
        for line in data[1:]:
            if line.find(b'=') <= 0:
                wtf.append(line)
            else:
                if wtf:
                    ret['header']['unparsed'] = b'\x00'.join(wtf)
                    wtf = []

                line = line.decode('utf-8').split('=')
                ret[line[0]] = '='.join(line[1:])

        del ret['value']
        return [ret]


class UeventSocket(NetlinkSocket):
    def __init__(self):
        super(UeventSocket, self).__init__(NETLINK_KOBJECT_UEVENT)
        self.marshal = MarshalUevent()

    def bind(self):
        return super(UeventSocket, self).bind(groups=-1)
