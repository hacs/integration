"""Verify network."""
import requests


def internet_connectivity_check():
    """Verify network connectivity."""
    hosts = [{"host": "https://github.com", "connection": False}]

    for host in hosts:
        try:
            requests.get(host["host"])

            host["connection"] = True
        except Exception:  # pylint: disable=broad-except
            host["connection"] = False

    return False not in [x["connection"] for x in hosts]
