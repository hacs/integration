import errno
import os
import threading

import mitogen.core
import mitogen.master

from pyroute2.iproute.linux import RTNL_API
from pyroute2.netlink.rtnl.iprsocket import MarshalRtnl

from .transport import RemoteSocket, Server, Transport


class Channel(object):
    def __init__(self, ch):
        self.ch = ch
        self._pfdr, self._pfdw = os.pipe()
        self.th = None
        self.closed = False
        self.lock = threading.RLock()
        self.shutdown_lock = threading.RLock()
        self.read = self._read_sync
        self.buf = ''

    def flush(self):
        pass

    def _read_sync(self, size):
        with self.lock:
            if self.buf:
                ret = self.buf[:size]
                self.buf = self.buf[size:]
                return ret
            ret = self.ch.get().unpickle()
            if len(ret) > size:
                self.buf = ret[size:]
            return ret[:size]

    def _read_async(self, size):
        with self.lock:
            return os.read(self._pfdr, size)

    def write(self, data):
        with self.lock:
            self.ch.send(data)
            return len(data)

    def start(self):
        with self.lock:
            if self.th is None:
                self.read = self._read_async
                self.th = threading.Thread(
                    target=self._monitor_thread,
                    name='Channel <%s> I/O' % self.ch,
                )
                self.th.start()

    def fileno(self):
        return self._pfdr

    def close(self):
        with self.shutdown_lock:
            if not self.closed:
                os.close(self._pfdw)
                os.close(self._pfdr)
                if self.th is not None:
                    self.th.join()
                self.closed = True
                if hasattr(self.ch, 'send'):
                    self.ch.send(None)

    def _monitor_thread(self):
        while True:
            msg = self.ch.get().unpickle()
            if msg is None:
                raise EOFError()
            os.write(self._pfdw, msg)


@mitogen.core.takes_router
def MitogenServer(ch_out, netns, target, router):
    ch_in = mitogen.core.Receiver(router)
    ch_out.send(ch_in.to_sender())

    trnsp_in = Transport(Channel(ch_in))
    trnsp_in.file_obj.start()
    trnsp_out = Transport(Channel(ch_out))

    return Server(trnsp_in, trnsp_out, netns, target)


class RemoteIPRoute(RTNL_API, RemoteSocket):
    def __init__(self, *argv, **kwarg):
        self._argv = tuple(argv)
        self._kwarg = dict(kwarg)
        if 'router' in kwarg:
            self._mitogen_broker = None
            self._mitogen_router = kwarg.pop('router')
        else:
            self._mitogen_broker = mitogen.master.Broker()
            self._mitogen_router = mitogen.master.Router(self._mitogen_broker)

        netns = kwarg.pop('netns', None)
        target = kwarg.pop('target', 'remote')
        try:
            if 'context' in kwarg:
                context = kwarg['context']
            else:
                protocol = kwarg.pop('protocol', 'local')
                context = getattr(self._mitogen_router, protocol)(
                    *argv, **kwarg
                )
            ch_in = mitogen.core.Receiver(
                self._mitogen_router, respondent=context
            )
            self._mitogen_call = context.call_async(
                MitogenServer,
                ch_out=ch_in.to_sender(),
                netns=netns,
                target=target,
            )
            ch_out = ch_in.get().unpickle()
            super(RemoteIPRoute, self).__init__(
                Transport(Channel(ch_in)), Transport(Channel(ch_out))
            )
        except Exception:
            if self._mitogen_broker is not None:
                self._mitogen_broker.shutdown()
                self._mitogen_broker.join()
            raise
        self.marshal = MarshalRtnl()
        self.target = target
        self.groups = 67372509

    def clone(self):
        return type(self)(*self._argv, **self._kwarg)

    def close(self, code=errno.ECONNRESET):
        with self.shutdown_lock:
            if not self.closed:
                super(RemoteIPRoute, self).close(code=code)
                self.closed = True
                try:
                    self._mitogen_call.get()
                except mitogen.core.ChannelError:
                    pass
                if self._mitogen_broker is not None:
                    self._mitogen_broker.shutdown()
                    self._mitogen_broker.join()
