# -*- coding: utf-8 -*-
"""async_upnp_client.cli module."""
# pylint: disable=invalid-name

import argparse
import asyncio
import json
import logging
import operator
import sys
import time
from datetime import datetime
from typing import Any, Optional, Sequence, Tuple, Union, cast

from async_upnp_client.advertisement import SsdpAdvertisementListener
from async_upnp_client.aiohttp import AiohttpNotifyServer, AiohttpRequester
from async_upnp_client.client import UpnpDevice, UpnpService, UpnpStateVariable
from async_upnp_client.client_factory import UpnpFactory
from async_upnp_client.const import AddressTupleVXType
from async_upnp_client.exceptions import UpnpResponseError
from async_upnp_client.profiles.dlna import dlna_handle_notify_last_change
from async_upnp_client.search import async_search as async_ssdp_search
from async_upnp_client.ssdp import SSDP_IP_V4, SSDP_IP_V6, SSDP_PORT, SSDP_ST_ALL
from async_upnp_client.utils import CaseInsensitiveDict, get_local_ip

logging.basicConfig()
_LOGGER = logging.getLogger("upnp-client")
_LOGGER.setLevel(logging.ERROR)
_LOGGER_LIB = logging.getLogger("async_upnp_client")
_LOGGER_LIB.setLevel(logging.ERROR)
_LOGGER_TRAFFIC = logging.getLogger("async_upnp_client.traffic")
_LOGGER_TRAFFIC.setLevel(logging.ERROR)


parser = argparse.ArgumentParser(description="upnp_client")
parser.add_argument("--debug", action="store_true", help="Show debug messages")
parser.add_argument("--debug-traffic", action="store_true", help="Show network traffic")
parser.add_argument(
    "--pprint", action="store_true", help="Pretty-print (indent) JSON output"
)
parser.add_argument("--timeout", type=int, help="Timeout for connection", default=4)
parser.add_argument(
    "--strict", action="store_true", help="Be strict about invalid data received"
)
parser.add_argument(
    "--iso8601", action="store_true", help="Print timestamp in ISO8601 format"
)

subparsers = parser.add_subparsers(title="Command", dest="command")
subparsers.required = True

subparser = subparsers.add_parser("call-action", help="Call an action")
subparser.add_argument("device", help="URL to device description XML")
subparser.add_argument(
    "call-action", nargs="+", help="service/action param1=val1 param2=val2"
)

subparser = subparsers.add_parser("subscribe", help="Subscribe to services")
subparser.add_argument("device", help="URL to device description XML")
subparser.add_argument(
    "service", nargs="+", help="service type or part or abbreviation"
)
subparser.add_argument(
    "--nolastchange", action="store_true", help="Do not show LastChange events"
)

subparser = subparsers.add_parser("search", help="Search for devices")
subparser.add_argument("--bind", help="ip to bind to, e.g., 192.168.0.10")
subparser.add_argument(
    "--target",
    help="target ip, e.g., 192.168.0.10 or FF02::C%%6 to request from",
)
subparser.add_argument(
    "--target_port",
    help="port, e.g., 1900 or 1892 to request from",
    default=SSDP_PORT,
    type=int,
)
subparser.add_argument(
    "--search_target",
    help="search target to search for",
    default=SSDP_ST_ALL,
)

subparser = subparsers.add_parser("advertisements", help="Listen for advertisements")
subparser.add_argument(
    "--bind",
    help="ip to bind to, e.g., 192.168.0.10",
)
subparser.add_argument(
    "--target",
    help="target ip, e.g., 239.255.255.250 or FF02::C to listen to",
)
subparser.add_argument(
    "--target_port",
    help="port, e.g., 1900 or 1892 to request from",
    default=SSDP_PORT,
    type=int,
)

args = parser.parse_args()
pprint_indent = 4 if args.pprint else None

event_handler = None


async def create_device(description_url: str) -> UpnpDevice:
    """Create UpnpDevice."""
    timeout = args.timeout
    requester = AiohttpRequester(timeout)
    non_strict = not args.strict
    factory = UpnpFactory(requester, non_strict=non_strict)
    return await factory.async_create_device(description_url)


def get_timestamp() -> Union[str, float]:
    """Timestamp depending on configuration."""
    if args.iso8601:
        return datetime.now().isoformat(" ")
    return time.time()


def service_from_device(device: UpnpDevice, service_name: str) -> Optional[UpnpService]:
    """Get UpnpService from UpnpDevice by name or part or abbreviation."""
    for service in device.all_services:
        part = service.service_id.split(":")[-1]
        abbr = "".join([c for c in part if c.isupper()])
        if service_name in (service.service_type, part, abbr):
            return service

    return None


def on_event(
    service: UpnpService, service_variables: Sequence[UpnpStateVariable]
) -> None:
    """Handle a UPnP event."""
    _LOGGER.debug(
        "State variable change for %s, variables: %s",
        service,
        ",".join([sv.name for sv in service_variables]),
    )
    obj = {
        "timestamp": get_timestamp(),
        "service_id": service.service_id,
        "service_type": service.service_type,
        "state_variables": {sv.name: sv.value for sv in service_variables},
    }

    # special handling for DLNA LastChange state variable
    if len(service_variables) == 1 and service_variables[0].name == "LastChange":
        if not args.nolastchange:
            print(json.dumps(obj, indent=pprint_indent))
        last_change = service_variables[0]
        dlna_handle_notify_last_change(last_change)
    else:
        print(json.dumps(obj, indent=pprint_indent))


async def call_action(description_url: str, call_action_args: Sequence) -> None:
    """Call an action and show results."""
    # pylint: disable=too-many-locals
    device = await create_device(description_url)

    if "/" in call_action_args[0]:
        service_name, action_name = call_action_args[0].split("/")
    else:
        service_name = call_action_args[0]
        action_name = ""

    for action_arg in call_action_args[1:]:
        if "=" not in action_arg:
            print(f"Invalid argument value: {action_arg}")
            print("Use: Argument=value")
            sys.exit(1)

    action_args = {a.split("=", 1)[0]: a.split("=", 1)[1] for a in call_action_args[1:]}

    # get service
    service = service_from_device(device, service_name)
    if not service:
        services_str = "\n".join(
            [
                "  " + device_service.service_id.split(":")[-1]
                for device_service in device.all_services
            ]
        )
        print(f"Unknown service: {service_name}")
        print(f"Available services:\n{services_str}")
        sys.exit(1)

    # get action
    if not service.has_action(action_name):
        actions_str = "\n".join([f"  {name}" for name in sorted(service.actions)])
        print(f"Unknown action: {action_name}")
        print(f"Available actions:\n{actions_str}")
        sys.exit(1)
    action = service.action(action_name)

    # get in variables
    coerced_args = {}
    for key, value in action_args.items():
        in_arg = action.argument(key)
        if not in_arg:
            arguments_str = ",".join([a.name for a in action.in_arguments()])
            print(f"Unknown argument: {key}")
            print(f"Available arguments: {arguments_str}")
            sys.exit(1)
        coerced_args[key] = in_arg.coerce_python(value)

    # ensure all in variables given
    for in_arg in action.in_arguments():
        if in_arg.name not in action_args:
            in_args = "\n".join(
                [
                    f"  {in_arg.name}"
                    for in_arg in sorted(
                        action.in_arguments(), key=operator.attrgetter("name")
                    )
                ]
            )
            print("Missing in-arguments")
            print(f"Known in-arguments:\n{in_args}")
            sys.exit(1)

    _LOGGER.debug(
        "Calling %s.%s, parameters:\n%s",
        service.service_id,
        action.name,
        "\n".join([f"{key}:{value}" for key, value in coerced_args.items()]),
    )
    result = await action.async_call(**coerced_args)

    _LOGGER.debug(
        "Results:\n%s",
        "\n".join([f"{key}:{value}" for key, value in coerced_args.items()]),
    )

    obj = {
        "timestamp": get_timestamp(),
        "service_id": service.service_id,
        "service_type": service.service_type,
        "action": action.name,
        "in_parameters": coerced_args,
        "out_parameters": result,
    }
    print(json.dumps(obj, indent=pprint_indent))


async def subscribe(description_url: str, service_names: Any) -> None:
    """Subscribe to service(s) and output updates."""
    global event_handler  # pylint: disable=global-statement

    device = await create_device(description_url)

    # start notify server/event handler
    source = (get_local_ip(device.device_url), 0)
    server = AiohttpNotifyServer(device.requester, source=source)
    await server.async_start_server()
    _LOGGER.debug("Listening on: %s", server.callback_url)

    # gather all wanted services
    if "*" in service_names:
        service_names = [service.service_type for service in device.all_services]

    services = []
    for service_name in service_names:
        service = service_from_device(device, service_name)
        if not service:
            print(f"Unknown service: {service_name}")
            sys.exit(1)
        service.on_event = on_event
        services.append(service)

    # subscribe to services
    event_handler = server.event_handler
    for service in services:
        try:
            await event_handler.async_subscribe(service)
        except UpnpResponseError as ex:
            _LOGGER.error("Unable to subscribe to %s: %s", service, ex)

    # keep the webservice running
    while True:
        await asyncio.sleep(120)
        await event_handler.async_resubscribe_all()


def source_target(
    source: Optional[str],
    target: Optional[str],
    target_port: int,
) -> Tuple[AddressTupleVXType, AddressTupleVXType]:
    """Determine source/target."""
    # pylint: disable=too-many-branches, too-many-return-statements
    if source is None and target is None:
        return (
            "0.0.0.0",
            0,
        ), (SSDP_IP_V4, SSDP_PORT)

    if source is not None and target is None:
        if ":" not in source:
            # IPv4
            return (source, 0), (SSDP_IP_V4, SSDP_PORT)

        # IPv6
        if "%" in source:
            idx = source.index("%")
            source_ip, scope_id = source[:idx], int(source[idx + 1 :])
        else:
            source_ip, scope_id = source, 0

        return (source_ip, 0, 0, scope_id), (SSDP_IP_V6, SSDP_PORT, 0, scope_id)

    if source is None and target is not None:
        if ":" not in target:
            # IPv4
            return (
                "0.0.0.0",
                0,
            ), (target, target_port or SSDP_PORT)

        # IPv6
        if "%" in target:
            idx = target.index("%")
            target_ip, scope_id = target[:idx], int(target[idx + 1 :])
        else:
            target_ip, scope_id = target, 0

        return ("::", 0, 0, scope_id), (
            target_ip,
            target_port or SSDP_PORT,
            0,
            scope_id,
        )

    source_version = 6 if ":" in (source or "") else 4
    target_version = 6 if ":" in (target or "") else 4
    if source is not None and target is not None and source_version != target_version:
        print("Error: Source and target do not match protocol")
        sys.exit(1)

    if source is not None and target is not None and ":" in target:
        if "%" in target:
            idx = target.index("%")
            target_ip, scope_id = target[:idx], int(target[idx + 1 :])
        else:
            target_ip, scope_id = target, 0
        return (source, 0, 0, scope_id), (target_ip, target_port, 0, scope_id)

    return (cast(str, source), 0), (cast(str, target), target_port)


async def search(search_args: Any) -> None:
    """Discover devices."""
    timeout = args.timeout
    search_target = search_args.search_target
    source, target = source_target(
        search_args.bind, search_args.target, search_args.target_port
    )

    async def on_response(headers: CaseInsensitiveDict) -> None:
        print(
            json.dumps(
                {key: str(value) for key, value in headers.items()},
                indent=pprint_indent,
            )
        )

    await async_ssdp_search(
        search_target=search_target,
        source=source,
        target=target,
        timeout=timeout,
        async_callback=on_response,
    )


async def advertisements(advertisement_args: Any) -> None:
    """Listen for advertisements."""
    source, target = source_target(
        advertisement_args.bind,
        advertisement_args.target,
        advertisement_args.target_port,
    )

    async def on_notify(headers: CaseInsensitiveDict) -> None:
        print(
            json.dumps(
                {key: str(value) for key, value in headers.items()},
                indent=pprint_indent,
            )
        )

    listener = SsdpAdvertisementListener(
        async_on_alive=on_notify,
        async_on_byebye=on_notify,
        async_on_update=on_notify,
        source=source,
        target=target,
    )
    await listener.async_start()
    try:
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        _LOGGER.debug("KeyboardInterrupt")
        await listener.async_stop()
        raise


async def async_main() -> None:
    """Async main."""
    if args.debug:
        _LOGGER.setLevel(logging.DEBUG)
        _LOGGER_LIB.setLevel(logging.DEBUG)
        _LOGGER_TRAFFIC.setLevel(logging.INFO)
    if args.debug_traffic:
        _LOGGER_TRAFFIC.setLevel(logging.DEBUG)

    if args.command == "call-action":
        await call_action(args.device, getattr(args, "call-action"))
    elif args.command == "subscribe":
        await subscribe(args.device, args.service)
    elif args.command == "search":
        await search(args)
    elif args.command == "advertisements":
        await advertisements(args)


def main() -> None:
    """Set up async loop and run the main program."""
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(async_main())
    except KeyboardInterrupt:
        if event_handler:
            loop.run_until_complete(event_handler.async_unsubscribe_all())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
