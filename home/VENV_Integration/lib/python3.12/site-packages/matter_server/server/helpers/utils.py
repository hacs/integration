"""Utils for Matter server."""

import asyncio
from contextlib import suppress
import platform

import async_timeout

PLATFORM_MAC = platform.system() == "Darwin"


async def ping_ip(ip_address: str, timeout: int = 2, attempts: int = 1) -> bool:  # noqa: ASYNC109 timeout parameter required for native ping timeout
    """Ping given (IPv4 or IPv6) IP-address."""
    is_ipv6 = ":" in ip_address
    if is_ipv6 and PLATFORM_MAC:
        # macos does not have support for -W (timeout) on ping6 ?!
        cmd = f"ping6 -c 1 {ip_address}"
    elif is_ipv6:
        cmd = f"ping -6 -c 1 -W {timeout} {ip_address}"
    else:
        cmd = f"ping -c 1 -W {timeout} {ip_address}"
    while attempts:
        attempts -= 1
        try:
            # we add an additional timeout here as safeguard and to account for the fact
            # that macos does not seem to have timeout on ping6
            async with async_timeout.timeout(timeout + 2):
                success = (await check_output(cmd))[0] == 0
                if success or not attempts:
                    return success
        except asyncio.TimeoutError:
            pass
        # sleep between attempts
        await asyncio.sleep(10)
    return False


async def check_output(shell_cmd: str) -> tuple[int | None, bytes]:
    """Run shell subprocess and return output."""
    proc = await asyncio.create_subprocess_shell(
        shell_cmd,
        stderr=asyncio.subprocess.STDOUT,
        stdout=asyncio.subprocess.PIPE,
    )
    try:
        stdout, _ = await proc.communicate()
    except asyncio.CancelledError:
        with suppress(ProcessLookupError):
            proc.terminate()
            await proc.communicate()
        raise
    return (proc.returncode, stdout)
