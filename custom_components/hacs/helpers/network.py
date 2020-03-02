"""Verify network."""
from socket import gaierror
from pythonping import ping
from integrationhelper import Logger


def internet_connectivity_check(host="api.github.com"):
    """Verify network connectivity."""
    logger = Logger("hacs.network.check")
    try:
        result = ping(host, count=1, timeout=3)
        if result.success():
            logger.info("All good")
            return True
    except gaierror:
        logger.error(f"DNS issues, could not resolve {host}")
    return False
