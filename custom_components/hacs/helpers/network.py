"""Verify network."""
import socket


def internet_connectivity_check():
    """Verify network connectivity."""
    hosts = [{"host": "github.com", "port": 443, "connection": False}]

    for host in hosts:
        try:
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(
                (host["host"], host["port"])
            )

            host["connection"] = True
        except socket.error:
            host["connection"] = False

    return False not in [x["connection"] for x in hosts]
