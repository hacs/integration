"""SniTun Exceptions."""


class SniTunError(Exception):
    """Base Exception for SniTun exceptions."""


class SniTunChallengeError(SniTunError):
    """Raise if a challenge error is occure."""


class SniTunInvalidPeer(SniTunError):
    """Raise if peer config is invalid."""


class ParseSNIError(SniTunError):
    """Invalid ClientHello data."""


class ParseSNIIncompleteError(ParseSNIError):
    """Incomplete ClientHello data."""


class MultiplexerTransportError(SniTunError):
    """Raise if multiplexer have an problem with peer."""


class MultiplexerTransportClose(SniTunError):
    """Raise if connection to peer is closed."""


class MultiplexerTransportDecrypt(SniTunError):
    """Raise if decryption of message fails."""


class SniTunConnectionError(SniTunError):
    """Raise if SniTun client can't connect to server."""
