import pickle
import select
import socket
import struct
import time
import uuid


class IdCache(dict):
    def invalidate(self):
        current_time = time.time()
        collect_time = current_time - 60
        for mid, meta in tuple(self.items()):
            if meta < collect_time:
                self.pop(mid)

    def __setitem__(self, key, value):
        if len(self) > 100:
            self.invalidate()
        dict.__setitem__(self, key, value)


class Peer(object):
    def __init__(self, remote_id, local_id, address, port, cache):
        self.address = address
        self.port = port
        self.socket = None
        self.remote_id = remote_id
        self.local_id = local_id
        self.cache = cache
        self.version = 0
        self.last_exception_time = 0

    @property
    def connected(self):
        return self.socket is not None

    def __repr__(self):
        if self.connected:
            connected = 'not connected'
        else:
            connected = 'connected'
        return '[%s-%s] %s:%s [%s]' % (
            self.local_id,
            self.remote_id,
            self.address,
            self.port,
            connected,
        )

    def hello(self):
        while True:
            message_id = str(uuid.uuid4().hex)
            if message_id not in self.cache:
                self.cache[message_id] = time.time()
                break
        data = pickle.dumps(
            {'type': 'system', 'id': message_id, 'data': 'HELLO'}
        )
        self.send(data)

    def send(self, data):
        length = len(data)
        data = struct.pack('III', length, self.version, self.local_id) + data
        if self.socket is None:
            if time.time() - self.last_exception_time < 5:
                return
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.socket.connect((self.address, self.port))
                self.hello()
            except Exception:
                self.last_exception_time = time.time()
                self.socket = None
                return
        try:
            self.socket.send(data)
        except Exception:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None

    def close(self):
        self.socket.close()


class Transport(object):
    def __init__(self, address, port):
        self.peers = []
        self.address = address
        self.port = port
        self.version = 0
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1048576)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.address, self.port))
        self.socket.listen(16)
        self.stream_endpoints = []

    def add_peer(self, peer):
        self.peers.append(peer)

    def send(self, data, exclude=None):
        exclude = exclude or []
        ret = []
        for peer in self.peers:
            if peer.remote_id not in exclude:
                ret.append(peer.send(data))
        return ret

    def get(self):
        while True:
            fds = [self.socket] + self.stream_endpoints
            [rlist, wlist, xlist] = select.select(fds, [], fds)
            for fd in xlist:
                if fd in self.stream_endpoints:
                    (
                        self.stream_endpoints.pop(
                            self.stream_endpoints.index(fd)
                        )
                    )
            for fd in rlist:
                if fd == self.socket:
                    new_fd, raddr = self.socket.accept()
                    self.stream_endpoints.append(new_fd)
                else:
                    data = fd.recv(8)
                    if len(data) == 0:
                        (
                            self.stream_endpoints.pop(
                                self.stream_endpoints.index(fd)
                            )
                        )
                        continue
                    length, version, remote_id = struct.unpack('III', data)
                    if version != self.version:
                        continue
                    data = b''
                    while len(data) < length:
                        data += fd.recv(length - len(data))
                    return data, remote_id

    def close(self):
        self.socket.close()


class Messenger(object):
    def __init__(self, local_id, transport=None):
        self.local_id = local_id
        self.transport = transport or Transport('127.0.0.1', 5680)
        self.targets = set()
        self.id_cache = IdCache()

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            msg = self.handle()
            if msg is not None:
                return msg

    def handle(self):
        data, remote_id = self.transport.get()
        message = pickle.loads(data)

        if message['id'] in self.id_cache:
            # discard message
            return None

        if message['type'] == 'system':
            # forward system messages
            self.transport.send(data, exclude=[remote_id])
            return message

        self.id_cache[message['id']] = time.time()

        if (
            message['type'] == 'transport'
            and message['target'] in self.targets
        ):
            # ignore DB updates with the same target
            message = None
        elif (
            message['type'] == 'api' and message['target'] not in self.targets
        ):
            # ignore API messages with other targets
            message = None

        self.transport.send(data, exclude=[remote_id])
        return message

    def emit(self, message):
        while True:
            message_id = '%s-%s' % (
                message.get('target', '-'),
                uuid.uuid4().hex,
            )
            if message_id not in self.id_cache:
                self.id_cache[message_id] = time.time()
                break

        message['id'] = message_id
        return self.transport.send(pickle.dumps(message))

    def add_peer(self, remote_id, address, port):
        peer = Peer(remote_id, self.local_id, address, port, self.id_cache)
        self.transport.add_peer(peer)
