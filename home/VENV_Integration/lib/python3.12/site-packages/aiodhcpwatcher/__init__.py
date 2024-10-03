__version__ = "1.0.2"

import asyncio
import logging
import os
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Iterable

from scapy.config import conf
from scapy.error import Scapy_Exception

if TYPE_CHECKING:
    from scapy.packet import Packet

_LOGGER = logging.getLogger(__name__)

FILTER = "udp and (port 67 or 68)"
DHCP_REQUEST = 3


@dataclass(slots=True)
class DHCPRequest:
    """Class to hold a DHCP request."""

    ip_address: str
    hostname: str
    mac_address: str


def make_packet_handler(
    callback: Callable[[DHCPRequest], None]
) -> Callable[["Packet"], None]:
    """Create a packet handler."""
    # Local import because importing from scapy has side effects such as opening
    # sockets
    from scapy.layers.dhcp import DHCP  # pylint: disable=import-outside-toplevel
    from scapy.layers.inet import IP  # pylint: disable=import-outside-toplevel
    from scapy.layers.l2 import Ether  # pylint: disable=import-outside-toplevel

    def _handle_dhcp_packet(packet: "Packet") -> None:
        """Process a dhcp packet."""
        if not (dhcp_packet := packet.getlayer(DHCP)):
            return

        options: Iterable[tuple[str, int | bytes | None]] = dhcp_packet.options

        options_dict: dict[str, int | bytes | None] = {}
        for option in options:
            if type(option) is tuple and len(option) > 1:
                options_dict[option[0]] = option[1]
            if option == "end":
                break

        if options_dict.get("message-type") != DHCP_REQUEST:
            # Not a DHCP request
            return

        ip_address: str = options_dict.get("requested_addr") or packet.getlayer(IP).src  # type: ignore[assignment]

        hostname = ""
        if (hostname_bytes := options_dict.get("hostname")) and isinstance(
            hostname_bytes, bytes
        ):
            try:
                # The standard uses idna encoding for hostnames, but some clients
                # do not follow the standard and use utf-8 instead.
                hostname = hostname_bytes.decode("idna")
            except UnicodeDecodeError:
                hostname = hostname_bytes.decode("utf-8", errors="replace")

        mac_address: str = packet.getlayer(Ether).src

        if ip_address is not None and mac_address is not None:
            callback(DHCPRequest(ip_address, hostname, mac_address))

    return _handle_dhcp_packet


class AIODHCPWatcher:
    """Class to watch dhcp requests."""

    _init_scapy_done = False

    def __init__(self, callback: Callable[[DHCPRequest], None]) -> None:
        """Initialize watcher."""
        self._loop = asyncio.get_running_loop()
        self._sock: Any | None = None
        self._fileno: int | None = None
        self._callback = callback

    def stop(self) -> None:
        """Stop watching for DHCP packets."""
        if self._sock and self._fileno:
            self._loop.remove_reader(self._fileno)
            self._sock.close()
            self._sock = None
            self._fileno = None

    def _start(self) -> Callable[["Packet"], None] | None:
        """Start watching for dhcp packets."""
        _init_scapy()
        # disable scapy promiscuous mode as we do not need it
        conf.sniff_promisc = 0

        try:
            self._verify_working_pcap(FILTER)
        except (Scapy_Exception, ImportError) as ex:
            _LOGGER.error(
                "Cannot watch for dhcp packets without a functional packet filter: %s",
                ex,
            )
            return None

        try:
            sock = self._make_listen_socket(FILTER)
            self._fileno = sock.fileno()
        except (Scapy_Exception, OSError) as ex:
            if os.geteuid() == 0:
                _LOGGER.error("Cannot watch for dhcp packets: %s", ex)
            else:
                _LOGGER.debug(
                    "Cannot watch for dhcp packets without root or CAP_NET_RAW: %s", ex
                )
            return None

        self._sock = sock
        return make_packet_handler(self._callback)

    async def async_start(self) -> None:
        """Start watching for dhcp packets."""
        if not (
            _handle_dhcp_packet := await asyncio.get_running_loop().run_in_executor(
                None, self._start
            )
        ):
            return
        sock = self._sock
        fileno = self._fileno
        if TYPE_CHECKING:
            assert sock is not None
            assert fileno is not None
        try:
            self._loop.add_reader(
                fileno, partial(self._on_data, _handle_dhcp_packet, sock)
            )
        except PermissionError as ex:
            _LOGGER.error("Permission denied to watch for dhcp packets: %s", ex)
            sock.close()
            self._sock = None
            self._fileno = None

    def _on_data(
        self, handle_dhcp_packet: Callable[["Packet"], None], sock: Any
    ) -> None:
        """Handle data from the socket."""
        try:
            data = sock.recv()
        except (BlockingIOError, InterruptedError):
            return
        except BaseException as ex:  # pylint: disable=broad-except
            _LOGGER.exception("Fatal error while processing dhcp packet: %s", ex)
            self.stop()

        if data:
            handle_dhcp_packet(data)

    def _make_listen_socket(self, cap_filter: str) -> Any:
        """Get a nonblocking listen socket."""
        from scapy.data import ETH_P_ALL  # pylint: disable=import-outside-toplevel
        from scapy.interfaces import (  # pylint: disable=import-outside-toplevel
            resolve_iface,
        )

        iface = conf.iface
        sock = resolve_iface(iface).l2listen()(
            type=ETH_P_ALL, iface=iface, filter=cap_filter
        )
        if hasattr(sock, "set_nonblock"):
            # Not all classes have set_nonblock so we have to call fcntl directly
            # in the event its not implemented
            sock.set_nonblock(True)
        elif hasattr(sock, "pcap_fd"):
            sock.pcap_fd.setnonblock(True)
        else:
            import fcntl  # pylint: disable=import-outside-toplevel

            fcntl.fcntl(sock.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)

        return sock

    def _verify_working_pcap(self, cap_filter: str) -> None:
        """
        Verify we can create a packet filter.

        If we cannot create a filter we will be listening for
        all traffic which is too intensive.
        """
        # Local import because importing from scapy has side effects such as opening
        # sockets
        from scapy.arch.common import (  # pylint: disable=import-outside-toplevel
            compile_filter,
        )

        compile_filter(cap_filter)


async def async_start(callback: Callable[[DHCPRequest], None]) -> Callable[[], None]:
    """Listen for DHCP requests."""
    watcher = AIODHCPWatcher(callback)
    await watcher.async_start()
    return watcher.stop


async def async_init() -> None:
    """Init scapy in the executor since it blocks for a bit."""
    await asyncio.get_running_loop().run_in_executor(None, _init_scapy)


def _init_scapy() -> None:
    """Init scapy in the executor since it blocks for a bit."""
    # Local import because importing from scapy has side effects such as opening
    # sockets
    # We must import l2 before testing the filter or it will fail

    #
    # Importing scapy.sendrecv will cause a scapy resync which will
    # import scapy.arch.read_routes which will import scapy.sendrecv
    #
    # We avoid this circular import by importing arch above to ensure
    # the module is loaded and avoid the problem
    #
    if AIODHCPWatcher._init_scapy_done:
        return
    from scapy import arch  # pylint: disable=import-outside-toplevel # noqa: F401
    from scapy.arch.common import (  # pylint: disable=import-outside-toplevel # noqa: F401
        compile_filter,
    )
    from scapy.layers import (
        l2,  # pylint: disable=import-outside-toplevel # noqa: F401
    )
    from scapy.layers.dhcp import (
        DHCP,  # pylint: disable=import-outside-toplevel # noqa: F401
    )
    from scapy.layers.inet import (
        IP,  # pylint: disable=import-outside-toplevel # noqa: F401
    )
    from scapy.layers.l2 import (
        Ether,  # pylint: disable=import-outside-toplevel # noqa: F401
    )

    AIODHCPWatcher._init_scapy_done = True


__all__ = ["start", "DHCPRequest", "make_packet_handler", "async_init"]
