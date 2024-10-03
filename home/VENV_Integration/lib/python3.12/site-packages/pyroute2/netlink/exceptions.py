import os
import time


class NetlinkError(Exception):
    '''
    Base netlink error
    '''

    def __init__(self, code, msg=None):
        msg = msg or os.strerror(code)
        super(NetlinkError, self).__init__(code, msg)
        self.code = code
        self.extra_code = 0


class NetlinkDecodeError(Exception):
    '''
    Base decoding error class.

    Incapsulates underlying error for the following analysis
    '''

    def __init__(self, exception):
        self.exception = exception


class NetlinkHeaderDecodeError(NetlinkDecodeError):
    '''
    The error occured while decoding a header
    '''

    pass


class NetlinkDataDecodeError(NetlinkDecodeError):
    '''
    The error occured while decoding the message fields
    '''

    pass


class NetlinkNLADecodeError(NetlinkDecodeError):
    '''
    The error occured while decoding NLA chain
    '''

    pass


class IPSetError(NetlinkError):
    '''
    Netlink error with IPSet special error codes.

    Messages are imported from errcode.c
    '''

    pass


class NetlinkDumpInterrupted(NetlinkError):
    '''
    Raised when NLM_F_DUMP_INTR is set in the flags.
    '''

    def __init__(self, code=-1, msg='dump interrupted'):
        super(NetlinkDumpInterrupted, self).__init__(code, msg)


class SkipInode(Exception):
    def __init__(self, code=0, msg=None):
        super(SkipInode, self).__init__(code, msg)
        self.code = code


class ChaoticException(Exception):
    def __init__(self):
        chaotic_id = str(time.time())
        super(ChaoticException, self).__init__(chaotic_id)
        self.chaotic_id = chaotic_id
