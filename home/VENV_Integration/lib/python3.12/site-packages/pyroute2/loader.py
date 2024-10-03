import struct
import sys

##
#
# Logging setup
#
# See the history:
#  * https://github.com/svinota/pyroute2/issues/246
#  * https://github.com/svinota/pyroute2/issues/255
#  * https://github.com/svinota/pyroute2/issues/270
#  * https://github.com/svinota/pyroute2/issues/573
#  * https://github.com/svinota/pyroute2/issues/601
#
from pyroute2.config import log

##
#
# Windows platform specific: socket module monkey patching
#
# To use the library on Windows, run::
#   pip install win-inet-pton
#
if sys.platform.startswith('win'):  # noqa: E402
    import win_inet_pton  # noqa: F401


def init():
    try:
        # probe, if the bytearray can be used in struct.unpack_from()
        struct.unpack_from('I', bytearray((1, 0, 0, 0)), 0)
    except Exception:
        if sys.version_info[0] < 3:
            # monkeypatch for old Python versions
            log.warning('patching struct.unpack_from()')

            def wrapped(fmt, buf, offset=0):
                return struct._u_f_orig(fmt, str(buf), offset)

            struct._u_f_orig = struct.unpack_from
            struct.unpack_from = wrapped
        else:
            raise
