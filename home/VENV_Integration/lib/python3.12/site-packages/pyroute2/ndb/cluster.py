import json
import socket

from pyroute2.common import basestring

from .main import NDB
from .transport import Messenger, Transport


def init(config):
    if isinstance(config, basestring):
        config = json.loads(config)
    else:
        config = json.load(config)
    hostname = config['local'].get('hostname', socket.gethostname())
    messenger = Messenger(
        config['local']['id'],
        Transport(config['local']['address'], config['local']['port']),
    )

    for target in config['local'].get('targets', []):
        messenger.targets.add(target)

    if not messenger.targets:
        messenger.targets.add(hostname)

    for peer in config.get('peers', []):
        messenger.add_peer(*peer)

    sources = config['local'].get('sources')
    if sources is None:
        sources = [{'target': hostname, 'kind': 'local'}]

    return NDB(
        log=config.get('log', 'debug'),
        sources=sources,
        localhost=sources[0]['target'],
        messenger=messenger,
    )
