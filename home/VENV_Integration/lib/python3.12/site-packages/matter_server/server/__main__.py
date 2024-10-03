"""Script entry point to run the Matter Server."""

import argparse
import asyncio
from contextlib import suppress
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import threading
from typing import Final

from aiorun import run
import coloredlogs

from matter_server.common.const import VERBOSE_LOG_LEVEL
from matter_server.common.helpers.logger import MatterFormatter, MatterNodeFilter
from matter_server.server import stack

from .server import MatterServer

DEFAULT_VENDOR_ID = 0xFFF1
DEFAULT_FABRIC_ID = 1
DEFAULT_PORT = 5580
# Default to None to bind to all addresses on both IPv4 and IPv6
DEFAULT_LISTEN_ADDRESS = None
DEFAULT_STORAGE_PATH = os.path.join(Path.home(), ".matter_server")

FORMAT_DATE: Final = "%Y-%m-%d"
FORMAT_TIME: Final = "%H:%M:%S"
FORMAT_DATETIME: Final = f"{FORMAT_DATE} {FORMAT_TIME}"
MAX_LOG_FILESIZE = 1000000 * 10  # 10 MB

# Get parsed passed in arguments.
parser = argparse.ArgumentParser(
    description="Matter Controller Server using WebSockets."
)


parser.add_argument(
    "--vendorid",
    type=int,
    default=DEFAULT_VENDOR_ID,
    help=f"Vendor ID for the Fabric, defaults to {DEFAULT_VENDOR_ID}",
)
parser.add_argument(
    "--fabricid",
    type=int,
    default=DEFAULT_FABRIC_ID,
    help=f"Fabric ID for the Fabric, defaults to {DEFAULT_FABRIC_ID}",
)
parser.add_argument(
    "--storage-path",
    type=str,
    default=DEFAULT_STORAGE_PATH,
    help=f"Storage path to keep persistent data, defaults to {DEFAULT_STORAGE_PATH}",
)
parser.add_argument(
    "--port",
    type=int,
    default=DEFAULT_PORT,
    help=f"TCP Port to run the websocket server, defaults to {DEFAULT_PORT}",
)
parser.add_argument(
    "--listen-address",
    type=str,
    action="append",
    default=DEFAULT_LISTEN_ADDRESS,
    help="IP address to bind the websocket server to, defaults to any IPv4 and IPv6 address.",
)
parser.add_argument(
    "--log-level",
    type=str,
    default="info",
    help="Global logging level. Example --log-level debug, default=info, possible=(critical, error, warning, info, debug, verbose)",
)
parser.add_argument(
    "--log-level-sdk",
    type=str,
    default="error",
    help="Matter SDK logging level. Example --log-level-sdk detail, default=error, possible=(none, error, progress, detail, automation)",
)
parser.add_argument(
    "--log-file",
    type=str,
    default=None,
    help="Log file to write to (optional).",
)
parser.add_argument(
    "--primary-interface",
    type=str,
    default=None,
    help="Primary network interface for link-local addresses (optional).",
)
parser.add_argument(
    "--paa-root-cert-dir",
    type=str,
    default=None,
    help="Directory where PAA root certificates are stored.",
)
parser.add_argument(
    "--enable-test-net-dcl",
    action="store_true",
    help="Enable PAA root certificates and other device information from test-net DCL.",
)
parser.add_argument(
    "--bluetooth-adapter",
    type=int,
    required=False,
    help="Optional bluetooth adapter (id) to enable direct commisisoning support.",
)
parser.add_argument(
    "--log-node-ids",
    type=int,
    nargs="+",
    help="List of node IDs to show logs from (applies only to server logs).",
)
parser.add_argument(
    "--ota-provider-dir",
    type=str,
    default=None,
    help="Directory where OTA Provider stores software updates and configuration.",
)
parser.add_argument(
    "--disable-server-interactions",
    action="store_false",
    help="Controls disabling server cluster interactions on a controller. This in turn disables advertisement of active controller operational identities.",
)

args = parser.parse_args()


def _setup_logging() -> None:
    log_fmt = (
        "%(asctime)s.%(msecs)03d (%(threadName)s) %(levelname)s [%(name)s] %(message)s"
    )
    node_log_fmt = "%(asctime)s.%(msecs)03d (%(threadName)s) %(levelname)s [%(name)s] <Node:%(node)s> %(message)s"
    custom_level_style = {
        **coloredlogs.DEFAULT_LEVEL_STYLES,
        "chip_automation": {"color": "green", "faint": True},
        "chip_detail": {"color": "green", "faint": True},
        "chip_progress": {},
        "chip_error": {"color": "red"},
    }
    custom_field_styles = {
        **coloredlogs.DEFAULT_FIELD_STYLES,
        "node": {"color": "magenta"},
    }
    # Let coloredlogs handle all levels, we filter levels in the logging module
    handler = coloredlogs.StandardErrorHandler(level=logging.NOTSET)
    handler.setFormatter(
        MatterFormatter(
            fmt=log_fmt,
            node_fmt=node_log_fmt,
            datefmt=FORMAT_DATETIME,
            level_styles=custom_level_style,
            field_styles=custom_field_styles,
        )
    )

    if args.log_node_ids:
        handler.addFilter(MatterNodeFilter(set(args.log_node_ids)))

    # Capture warnings.warn(...) and friends messages in logs.
    # The standard destination for them is stderr, which may end up unnoticed.
    # This way they're where other messages are, and can be filtered as usual.
    logging.captureWarnings(True)

    logging.addLevelName(VERBOSE_LOG_LEVEL, "VERBOSE")
    logging.basicConfig(level=args.log_level.upper(), handlers=[handler])

    # setup file handler
    logger = logging.getLogger()
    if args.log_file:
        log_filename = os.path.join(args.log_file)
        file_handler = RotatingFileHandler(
            log_filename, maxBytes=MAX_LOG_FILESIZE, backupCount=1
        )
        # rotate log at each start
        with suppress(OSError):
            file_handler.doRollover()
        file_handler.setFormatter(logging.Formatter(log_fmt, datefmt=FORMAT_DATETIME))
        logger.addHandler(file_handler)

    stack.init_logging(args.log_level_sdk.upper())
    logger.setLevel(args.log_level.upper())

    if not logger.isEnabledFor(VERBOSE_LOG_LEVEL):
        logging.getLogger("PersistentStorage").setLevel(logging.WARNING)
        # (temporary) raise the log level of zeroconf as its a logs an annoying
        # warning at startup while trying to bind to a loopback IPv6 interface
        logging.getLogger("zeroconf").setLevel(logging.ERROR)

    # register global uncaught exception loggers
    sys.excepthook = lambda *args: logger.exception(
        "Uncaught exception",
        exc_info=args,
    )
    threading.excepthook = lambda args: logger.exception(
        "Uncaught thread exception",
        exc_info=(  # type: ignore[arg-type]
            args.exc_type,
            args.exc_value,
            args.exc_traceback,
        ),
    )


def main() -> None:
    """Run main execution."""

    # make sure storage path exists
    if not os.path.isdir(args.storage_path):
        os.mkdir(args.storage_path)

    _setup_logging()

    # Init server
    server = MatterServer(
        args.storage_path,
        int(args.vendorid),
        int(args.fabricid),
        int(args.port),
        args.listen_address,
        args.primary_interface,
        args.paa_root_cert_dir,
        args.enable_test_net_dcl,
        args.bluetooth_adapter,
        args.ota_provider_dir,
        args.disable_server_interactions,
    )

    async def handle_stop(loop: asyncio.AbstractEventLoop) -> None:
        # pylint: disable=unused-argument
        await server.stop()

    # run the server
    run(server.start(), shutdown_callback=handle_stop)


if __name__ == "__main__":
    main()
