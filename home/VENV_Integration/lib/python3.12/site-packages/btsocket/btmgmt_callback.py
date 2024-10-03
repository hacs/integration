"""
Use callback-based programming style to read and write to BlueZ Management API
"""
import asyncio
from collections import deque

from btsocket import btmgmt_socket
from btsocket import btmgmt_protocol
from btsocket import tools

logger = tools.create_module_logger(__name__)


class Mgmt:

    def __init__(self):
        # Setup read and write sockets
        self.sock = btmgmt_socket.open()
        self.loop = asyncio.get_event_loop()
        # Store for event callbacks
        self._event_callbacks = dict()
        # Queue for commands to be written to BlueZ socket
        self.cmd_queue = deque()
        self.running = False

    def add_event_callback(self, event, callback):
        """
        Assign a callback to be called when a specific event happens.
        The callback should take two arguments.
          1) The response packet
          2) the AsyncMgmt() class instance object

        :param event: An entry from the enum btmgmt.Events
        :param callback: A callback function
        """
        self._event_callbacks[event] = callback

    def reader(self):
        """
        Read callback is called when data available on Bluetooth socket.
        Processes packet and hands-off to event callbacks that have subscribed
        to events.
        """
        logger.debug('Reader callback')
        data = self.sock.recv(100)
        pkt = btmgmt_protocol.reader(data)
        logger.info('pkt: [%s]', pkt)
        if pkt.header.event_code in self._event_callbacks:
            self._event_callbacks[pkt.header.event_code](pkt, self)
        if not self.running:
            self.stop()

    def writer(self):
        """
        Write callback when Bluetooth socket is available for writing.
        Takes commands that are on the cmd_queue and sends.
        """
        logger.debug('Writer callback')
        if len(self.cmd_queue) > 0:
            this_cmd = self.cmd_queue.popleft()
            logger.info('sending pkt [%s]', tools.format_pkt(this_cmd))
            self.sock.send(this_cmd)
        if not self.running and len(self.cmd_queue) == 0:
            self.loop.stop()
            # Do one more read to get the response from the last command
            self.reader()

    @staticmethod
    def _as_packet(pkt_objs):
        """Pack bytes together for sending"""
        full_pkt = b''
        for frame in pkt_objs:
            if frame:
                full_pkt += frame.octets
        return full_pkt

    def send(self, cmd, ctrl_idx, *params):
        """
        Add commands onto the queue ready to be sent.
        Basic structure of the command
        send(<command_name>, <adapter index>, <positional paramters>)

        :param cmd: A value from btmgmt.Commands
        :param ctrl_idx: The index of the controller [0xFFFF is non-controller]
        :param params: 0 or more input parameters for command
        """
        pkt_objs = btmgmt_protocol.command(cmd, ctrl_idx, *params)
        cmd_pkt = self._as_packet(pkt_objs)
        logger.debug('Queue command: %s', tools.format_pkt(cmd_pkt))
        self.cmd_queue.append(cmd_pkt)

    def stop(self):
        """
        Once all commands have been sent, exit the event loop
        """
        self.running = False

        self.loop.remove_writer(self.sock)
        self.loop.remove_reader(self.sock)
        self.loop.stop()

    def close(self):
        """
        Stop the event loop and close sockets etc.
        """
        btmgmt_socket.close(self.sock)
        # Stop the event loop
        self.loop.close()

    def start(self):
        self.running = True
        # Setup reader and writer for socket streams
        self.loop.add_reader(self.sock, self.reader)
        self.loop.add_writer(self.sock, self.writer)
        logger.debug('Starting event loop...')
        try:
            # Run the event loop
            self.loop.run_forever()
        except KeyboardInterrupt:
            self.loop.stop()
        finally:
            # We are done. Close sockets and the event loop.
            self.close()
