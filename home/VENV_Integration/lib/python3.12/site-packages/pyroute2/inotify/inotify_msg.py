import struct

from pyroute2.netlink import nlmsg_base, nlmsg_decoder_generic


class inotify_msg(nlmsg_base, nlmsg_decoder_generic):
    fields = (
        ('wd', 'i'),
        ('mask', 'I'),
        ('cookie', 'I'),
        ('name_length', 'I'),
    )

    def decode(self):
        super(inotify_msg, self).decode()
        (name,) = struct.unpack_from(
            '%is' % self['name_length'], self.data, self.offset + 16
        )
        self['name'] = name.decode('utf-8').strip('\0')
        self.length = self['name_length'] + 16
