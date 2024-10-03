"""SniTun worker for traffics."""

from __future__ import annotations

import asyncio
import logging
from multiprocessing import Manager, Process, Queue
from socket import socket
from threading import Thread
from typing import TYPE_CHECKING

from .listener_peer import PeerListener
from .listener_sni import SNIProxy
from .peer import Peer
from .peer_manager import PeerManager, PeerManagerEvent

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from multiprocessing.managers import SyncManager


class ServerWorker(Process):
    """Worker for multiplexer."""

    def __init__(
        self,
        fernet_keys: list[str],
        throttling: int | None = None,
    ) -> None:
        """Initialize worker & communication."""
        super().__init__()

        self._fernet_keys: list[str] = fernet_keys
        self._throttling: int | None = throttling

        # Used on the child
        self._peers: PeerManager | None = None
        self._list_sni: SNIProxy | None = None
        self._list_peer: PeerListener | None = None
        self._loop: asyncio.BaseEventLoop | None = None

        # Communication between Parent/Child
        self._manager: SyncManager = Manager()
        self._new: Queue = self._manager.Queue()
        self._sync: dict[str, None] = self._manager.dict()
        self._peer_count = self._manager.Value("peer_count", 0)

    @property
    def peer_size(self) -> int:
        """Return amount of managed peers."""
        return self._peer_count.value

    def is_responsible_peer(self, sni: str) -> bool:
        """Return True if worker is responsible for this peer domain."""
        return sni in self._sync

    async def _async_init(self) -> None:
        """Initialize child process data."""
        self._peers = PeerManager(
            self._fernet_keys,
            throttling=self._throttling,
            event_callback=self._event_stream,
        )
        self._list_sni = SNIProxy(self._peers)
        self._list_peer = PeerListener(self._peers)

    def _event_stream(self, peer: Peer, event: PeerManagerEvent) -> None:
        """Event stream peer connection data."""
        if event == PeerManagerEvent.CONNECTED:
            if peer.hostname not in self._sync:
                self._peer_count.set(self._peer_count.value + 1)
            for hostname in peer.all_hostnames:
                self._sync[hostname] = None
        else:
            if peer.hostname in self._sync:
                self._peer_count.set(self._peer_count.value - 1)
            for hostname in peer.all_hostnames:
                self._sync.pop(hostname, None)

    def shutdown(self) -> None:
        """Shutdown child process."""
        self._new.put(None)
        self.join(10)

    def handover_connection(
        self,
        con: socket,
        data: bytes,
        sni: str | None = None,
    ) -> None:
        """Move new connection to worker."""
        self._new.put_nowait((con, data, sni))

    def run(self) -> None:
        """Run the worker process."""
        _LOGGER.info("Start worker: %s", self.name)

        # Init new event loop
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        # Start eventloop
        running_loop = Thread(target=self._loop.run_forever)
        running_loop.start()

        # Init backend
        asyncio.run_coroutine_threadsafe(self._async_init(), loop=self._loop).result()

        while True:
            new = self._new.get()
            if new is None:
                break

            new[0].setblocking(False)
            asyncio.run_coroutine_threadsafe(
                self._async_new_connection(*new),
                loop=self._loop,
            )

        # Shutdown worker
        _LOGGER.info("Stoping worker: %s", self.name)
        asyncio.run_coroutine_threadsafe(
            self._peers.close_connections(),
            loop=self._loop,
        ).result()
        self._loop.call_soon_threadsafe(self._loop.stop)
        running_loop.join(10)

    async def _async_new_connection(
        self,
        con: socket,
        data: bytes,
        sni: str | None,
    ) -> None:
        """Handle incoming connection."""
        try:
            reader, writer = await asyncio.open_connection(sock=con)
        except OSError:
            con.close()
            return

        # Select the correct handler for process connection
        if sni:
            self._loop.create_task(
                self._list_sni.handle_connection(reader, writer, data=data, sni=sni),
            )
        else:
            self._loop.create_task(
                self._list_peer.handle_connection(reader, writer, data=data),
            )
