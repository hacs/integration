import asyncio
import ctypes
import socket
import sys


AF_BLUETOOTH = 31
PF_BLUETOOTH = AF_BLUETOOTH
SOCK_RAW = 3
BTPROTO_HCI = 1
SOCK_CLOEXEC = 524288
SOCK_NONBLOCK = 2048
HCI_CHANNEL_CONTROL = 3
HCI_DEV_NONE = 0xffff


class BluetoothSocketError(BaseException):
    pass


class BluetoothCommandError(BaseException):
    pass


class SocketAddr(ctypes.Structure):
    _fields_ = [
        ("hci_family", ctypes.c_ushort),
        ("hci_dev", ctypes.c_ushort),
        ("hci_channel", ctypes.c_ushort),
    ]


def open():
    """
    Because of the following issue with Python the Bluetooth User socket
    on linux needs to be done with lower level calls.
    https://bugs.python.org/issue36132
    Based on mgmt socket at:
    https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/mgmt-api.txt
    """

    sockaddr_hcip = ctypes.POINTER(SocketAddr)
    ctypes.cdll.LoadLibrary("libc.so.6")
    libc = ctypes.CDLL("libc.so.6")

    libc_socket = libc.socket
    libc_socket.argtypes = (ctypes.c_int, ctypes.c_int, ctypes.c_int)
    libc_socket.restype = ctypes.c_int

    bind = libc.bind
    bind.argtypes = (ctypes.c_int, ctypes.POINTER(SocketAddr), ctypes.c_int)
    bind.restype = ctypes.c_int

    # fd = libc_socket(PF_BLUETOOTH, SOCK_RAW | SOCK_CLOEXEC | SOCK_NONBLOCK,
    #               BTPROTO_HCI)
    fd = libc_socket(PF_BLUETOOTH, SOCK_RAW, BTPROTO_HCI)

    if fd < 0:
        raise BluetoothSocketError("Unable to open PF_BLUETOOTH socket")

    addr = SocketAddr()
    addr.hci_family = AF_BLUETOOTH  # AF_BLUETOOTH
    addr.hci_dev = HCI_DEV_NONE  # adapter index
    addr.hci_channel = HCI_CHANNEL_CONTROL  # HCI_USER_CHANNEL
    r = bind(fd, sockaddr_hcip(addr), ctypes.sizeof(addr))
    if r < 0:
        raise BluetoothSocketError("Unable to bind %s", r)

    sock_fd = socket.socket(AF_BLUETOOTH, SOCK_RAW, BTPROTO_HCI, fileno=fd)
    return sock_fd


def close(bt_socket):
    """Close the open socket"""
    fd = bt_socket.detach()
    socket.close(fd)


def test_asyncio_usage():
    sock = open()

    if sys.version_info < (3, 10):
        loop = asyncio.get_event_loop()
    else:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()

        asyncio.set_event_loop(loop)

    def reader():
        data = sock.recv(100)
        print("Received:", data)

        # We are done: unregister the file descriptor
        loop.remove_reader(sock)

        # Stop the event loop
        loop.stop()

    # Register the file descriptor for read event
    loop.add_reader(sock, reader)

    # Write a command to the socket
    # Read Management Version Information Command
    # b'\x01\x00\xff\xff\x00\x00'
    loop.call_soon(sock.send, b'\x01\x00\xff\xff\x00\x00')

    try:
        # Run the event loop
        loop.run_forever()
    finally:
        # We are done. Close sockets and the event loop.
        close(sock)
        loop.close()


if __name__ == '__main__':
    test_asyncio_usage()
