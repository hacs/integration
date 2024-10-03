import ctypes
import ctypes.util
import os
import select
import socket
import threading

from pyroute2.inotify.inotify_msg import inotify_msg


class Inotify(object):
    def __init__(self, libc=None, path=None):
        self.fd = None
        self.wd = {}
        self.ctlr, self.ctlw = os.pipe()
        self.path = set(path)
        self._poll = select.poll()
        self._poll.register(self.ctlr)
        self.lock = threading.RLock()
        self.libc = libc or ctypes.CDLL(
            ctypes.util.find_library('c'), use_errno=True
        )

    def bind(self, *argv, **kwarg):
        with self.lock:
            if self.fd is not None:
                raise socket.error(22, 'Invalid argument')
            self.fd = self.libc.inotify_init()
            self._poll.register(self.fd)
            for path in self.path:
                self.register_path(path)

    def register_path(self, path, mask=0x100 | 0x200):
        os.stat(path)
        with self.lock:
            if path in self.wd:
                return
            if self.fd is not None:
                s_path = ctypes.create_string_buffer(path.encode('utf-8'))
                wd = self.libc.inotify_add_watch(
                    self.fd, ctypes.byref(s_path), mask
                )
                self.wd[wd] = path
            self.path.add(path)

    def unregister_path(self):
        pass

    def get(self):
        #
        events = self._poll.poll()
        for fd, event in events:
            if fd == self.fd:
                data = os.read(self.fd, 4096)
                for msg in self.parse(data):
                    yield msg
            else:
                yield

    def close(self):
        with self.lock:
            if self.fd is not None:
                os.write(self.ctlw, b'\0')
            for fd in (self.fd, self.ctlw, self.ctlr):
                if fd is not None:
                    try:
                        os.close(fd)
                        self._poll.unregister(fd)
                    except Exception:
                        pass

    def parse(self, data):
        offset = 0

        while offset <= len(data) - 16:
            # pick one header
            msg = inotify_msg(data, offset=offset)
            msg.decode()
            if msg['wd'] == 0:
                break
            msg['path'] = self.wd[msg['wd']]
            offset += msg.length
            yield msg
