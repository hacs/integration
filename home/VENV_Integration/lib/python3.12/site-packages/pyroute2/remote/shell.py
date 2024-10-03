import atexit
import errno
import logging
import struct
import subprocess

from pyroute2.iproute import RTNL_API
from pyroute2.netlink.rtnl.iprsocket import MarshalRtnl
from pyroute2.remote.transport import RemoteSocket, Transport

log = logging.getLogger(__name__)


class ShellIPR(RTNL_API, RemoteSocket):
    def __init__(self, target):
        self.target = target
        cmd = '%s python -m pyroute2.remote' % target
        self.shell = subprocess.Popen(
            cmd.split(),
            bufsize=0,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        trnsp_in = Transport(self.shell.stdout)
        trnsp_out = Transport(self.shell.stdin)

        try:
            super(ShellIPR, self).__init__(trnsp_in, trnsp_out)
        except Exception:
            self.close()
            raise
        atexit.register(self.close)
        self.marshal = MarshalRtnl()

    def clone(self):
        return type(self)(self.target)

    def _cleanup_atexit(self):
        if hasattr(atexit, 'unregister'):
            atexit.unregister(self.close)
        else:
            try:
                atexit._exithandlers.remove((self.close, (), {}))
            except ValueError:
                pass

    def close(self, code=errno.ECONNRESET):
        self._cleanup_atexit()
        # something went wrong, force server shutdown
        try:
            self.trnsp_out.send({'stage': 'shutdown'})
            if code > 0:
                data = {
                    'stage': 'broadcast',
                    'data': struct.pack('IHHQIQQ', 28, 2, 0, 0, code, 0, 0),
                    'error': None,
                }
                self.trnsp_in.brd_queue.put(data)
        except Exception:
            pass
        # force cleanup command channels
        for close in (self.trnsp_in.close, self.trnsp_out.close):
            try:
                close()
            except Exception:
                pass  # Maybe already closed in remote.Client.close

        self.shell.kill()
        self.shell.wait()

    def post_init(self):
        pass
