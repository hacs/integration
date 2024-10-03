'''
Netlink proxy engine
'''

import errno
import logging
import struct
import threading
import traceback

from pyroute2.netlink.exceptions import NetlinkError

log = logging.getLogger(__name__)


class NetlinkProxy(object):
    '''
    Proxy schemes::

        User -> NetlinkProxy -> Kernel
                       |
             <---------+

        User <- NetlinkProxy <- Kernel

    '''

    def __init__(self, policy='forward', nl=None, lock=None):
        self.nl = nl
        self.lock = lock or threading.Lock()
        self.pmap = {}
        self.policy = policy

    def handle(self, msg):
        #
        # match the packet
        #
        ptype = msg['header']['type']
        plugin = self.pmap.get(ptype, None)
        if plugin is not None:
            with self.lock:
                try:
                    ret = plugin(msg, self.nl)
                    if ret is None:
                        #
                        # The packet is terminated in the plugin,
                        # return the NLMSG_ERR == 0
                        #
                        # FIXME: optimize
                        #
                        newmsg = struct.pack('IHH', 40, 2, 0)
                        newmsg += msg.data[8:16]
                        newmsg += struct.pack('I', 0)
                        # nlmsgerr struct alignment
                        newmsg += b'\0' * 20
                        return {'verdict': self.policy, 'data': newmsg}
                    else:
                        return ret

                except Exception as e:
                    log.error(''.join(traceback.format_stack()))
                    log.error(traceback.format_exc())
                    # errmsg
                    if isinstance(e, (OSError, IOError)):
                        code = e.errno
                    elif isinstance(e, NetlinkError):
                        code = e.code
                    else:
                        code = errno.ECOMM
                    newmsg = struct.pack('HH', 2, 0)
                    newmsg += msg.data[8:16]
                    newmsg += struct.pack('I', code)
                    newmsg += msg.data
                    newmsg = struct.pack('I', len(newmsg) + 4) + newmsg
                    return {'verdict': 'error', 'data': newmsg}
        return None
