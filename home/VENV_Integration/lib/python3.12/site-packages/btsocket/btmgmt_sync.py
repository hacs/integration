from btsocket import btmgmt_protocol
from btsocket import btmgmt_socket
from btsocket import tools

logger = tools.create_module_logger(__name__)


def _as_packet(pkt_objs):
    full_pkt = b''
    for frame in pkt_objs:
        if frame:
            full_pkt += frame.octets
    return full_pkt


def send(*args):
    response_recvd = False
    pkt_objs = btmgmt_protocol.command(*args)
    logger.debug('Sending btmgmt frames %s', pkt_objs)
    cmd_pkt = _as_packet(pkt_objs)
    # print('cmd pkt', [f'{octets:x}' for octets in cmd_pkt])
    sock = btmgmt_socket.open()
    logger.debug('Sending bytes: %s', cmd_pkt)
    sock.send(cmd_pkt)
    while not response_recvd:
        raw_data = sock.recv(100)
        logger.debug('Received: %s', raw_data)
        data = btmgmt_protocol.reader(raw_data)
        logger.debug('Received btmgmt frames: %s', data)
        if data.cmd_response_frame:
            response_recvd = True

    btmgmt_socket.close(sock)
    if data.event_frame.status != btmgmt_protocol.ErrorCodes.Success:
        raise NameError(f'btmgmt Error: '
                        f'{data.event_frame.command_opcode} '
                        f'{data.event_frame.status.name}')
    return data
