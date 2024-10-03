from __future__ import annotations

import ctypes

try:
    import fcntl
except ImportError:
    # fcntl is not available on Windows
    fcntl = None  # type: ignore
import logging
import socket
from typing import Any

_LOGGER = logging.getLogger(__name__)

AF_BLUETOOTH = 31
PF_BLUETOOTH = AF_BLUETOOTH
BTPROTO_HCI = 1
HCI_MAX_DEV = 16
HCIGETDEVLIST = 0x800448D2  # _IOR('H', 210, int)
HCIGETDEVINFO = 0x800448D3  # _IOR('H', 211, int)


class hci_dev_req(ctypes.Structure):
    _fields_ = [("dev_id", ctypes.c_uint16), ("dev_opt", ctypes.c_uint32)]


class hci_dev_list_req(ctypes.Structure):
    _fields_ = [("dev_num", ctypes.c_uint16), ("dev_req", hci_dev_req * HCI_MAX_DEV)]


class bdaddr_t(ctypes.Structure):
    _fields_ = [("b", ctypes.c_uint8 * 6)]

    def __str__(self) -> str:
        return ":".join(["%02X" % x for x in reversed(self.b)])


class hci_dev_stats(ctypes.Structure):
    _fields_ = [
        ("err_rx", ctypes.c_uint32),
        ("err_tx", ctypes.c_uint32),
        ("cmd_tx", ctypes.c_uint32),
        ("evt_rx", ctypes.c_uint32),
        ("acl_tx", ctypes.c_uint32),
        ("acl_rx", ctypes.c_uint32),
        ("sco_tx", ctypes.c_uint32),
        ("sco_rx", ctypes.c_uint32),
        ("byte_rx", ctypes.c_uint32),
        ("byte_tx", ctypes.c_uint32),
    ]


class hci_dev_info(ctypes.Structure):
    _fields_ = [
        ("dev_id", ctypes.c_uint16),
        ("name", ctypes.c_char * 8),
        ("bdaddr", bdaddr_t),
        ("flags", ctypes.c_uint32),
        ("type", ctypes.c_uint8),
        ("features", ctypes.c_uint8 * 8),
        ("pkt_type", ctypes.c_uint32),
        ("link_policy", ctypes.c_uint32),
        ("link_mode", ctypes.c_uint32),
        ("acl_mtu", ctypes.c_uint16),
        ("acl_pkts", ctypes.c_uint16),
        ("sco_mtu", ctypes.c_uint16),
        ("sco_pkts", ctypes.c_uint16),
        ("stat", hci_dev_stats),
    ]


hci_dev_info_p = ctypes.POINTER(hci_dev_info)


def get_adapters_from_hci() -> dict[int, dict[str, Any]]:
    """Get bluetooth adapters from HCI."""
    if not fcntl:
        raise RuntimeError("fcntl is not available")
    out: dict[int, dict[str, Any]] = {}
    sock: socket.socket | None = None
    try:
        sock = socket.socket(AF_BLUETOOTH, socket.SOCK_RAW, BTPROTO_HCI)
        buf = hci_dev_list_req()
        buf.dev_num = HCI_MAX_DEV
        ret = fcntl.ioctl(sock.fileno(), HCIGETDEVLIST, buf)
        if ret < 0:
            raise OSError(f"HCIGETDEVLIST failed: {ret}")
        for i in range(buf.dev_num):
            dev_req = buf.dev_req[i]
            dev = hci_dev_info()
            dev.dev_id = dev_req.dev_id
            ret = fcntl.ioctl(sock.fileno(), HCIGETDEVINFO, dev)
            info = {str(k): getattr(dev, k) for k, v_ in dev._fields_}
            info["bdaddr"] = str(info["bdaddr"])
            info["name"] = info["name"].decode()
            out[int(dev.dev_id)] = info
    except OSError as error:
        _LOGGER.debug("Error while getting HCI devices: %s", error)
        return out
    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.exception("Unexpected error while getting HCI devices: %s", error)
        return out
    finally:
        if sock:
            sock.close()
    return out
