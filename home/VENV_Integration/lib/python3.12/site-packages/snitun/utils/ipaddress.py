"""Utils for handling IP address."""
import ipaddress
import socket


def bytes_to_ip_address(data: bytes) -> ipaddress.IPv4Address:
    """Convert bytes into a IP address."""
    try:
        return ipaddress.ip_address(socket.inet_ntop(socket.AF_INET, data))
    except (ValueError, OSError):
        return ipaddress.ip_address(0)


def ip_address_to_bytes(ip_address: ipaddress.IPv4Address) -> bytes:
    """Convert a IP address object into bytes."""
    try:
        return socket.inet_pton(socket.AF_INET, str(ip_address))
    except OSError:
        return bytes(4)
