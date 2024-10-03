from pyroute2.common import map_namespace
from pyroute2.netlink import NLMSG_DONE
from pyroute2.netlink.nlsocket import Marshal

from . import ConnectorSocket, cn_msg

CN_IDX_PROC = 0x1

PROC_EVENT_NONE = 0x0
PROC_EVENT_FORK = 0x1
PROC_EVENT_EXEC = 0x2
PROC_EVENT_UID = 0x4
PROC_EVENT_GID = 0x40
PROC_EVENT_SID = 0x80
PROC_EVENT_PTRACE = 0x100
PROC_EVENT_COMM = 0x200
PROC_EVENT_COREDUMP = 0x40000000
PROC_EVENT_EXIT = 0x80000000

(PROC_BY_NAMES, PROC_BY_IDS) = map_namespace('PROC_', globals())

CN_IDX_PROC = 0x1
CN_VAL_PROC = 0x1

PROC_CN_MCAST_LISTEN = 0x1
PROC_CN_MCAST_IGNORE = 0x2


class proc_event_base(cn_msg):
    fields = cn_msg.fields + (
        ('what', 'I'),
        ('cpu', 'I'),
        ('timestamp_ns', 'Q'),
    )

    def decode(self):
        super().decode()
        self['event'] = PROC_BY_IDS.get(self['what'], 'UNDEFINED')


class proc_event_fork(proc_event_base):
    fields = proc_event_base.fields + (
        ('parent_pid', 'I'),
        ('parent_tgid', 'I'),
        ('child_pid', 'I'),
        ('child_tgid', 'I'),
    )


class proc_event_exec(proc_event_base):
    fields = proc_event_base.fields + (
        ('process_pid', 'I'),
        ('process_tgid', 'I'),
    )


class proc_event_uid(proc_event_base):
    fields = proc_event_base.fields + (
        ('process_pid', 'I'),
        ('process_tgid', 'I'),
        ('ruid', 'I'),
        ('rgid', 'I'),
    )


class proc_event_gid(proc_event_base):
    fields = proc_event_base.fields + (
        ('process_pid', 'I'),
        ('process_tgid', 'I'),
        ('euid', 'I'),
        ('egid', 'I'),
    )


class proc_event_sid(proc_event_base):
    fields = proc_event_base.fields + (
        ('process_pid', 'I'),
        ('process_tgid', 'I'),
    )


class proc_event_ptrace(proc_event_base):
    fields = proc_event_base.fields + (
        ('process_pid', 'I'),
        ('process_tgid', 'I'),
        ('tracer_pid', 'I'),
        ('tracer_tgid', 'I'),
    )


class proc_event_comm(proc_event_base):
    fields = proc_event_base.fields + (
        ('process_pid', 'I'),
        ('process_tgid', 'I'),
        ('comm', '16s'),
    )

    def decode(self):
        super().decode()
        self['comm'] = self['comm'].decode('utf-8').strip('\x00')


class proc_event_coredump(proc_event_base):
    fields = proc_event_base.fields + (
        ('process_pid', 'I'),
        ('process_tgid', 'I'),
        ('parent_pid', 'I'),
        ('parent_tgid', 'I'),
    )


class proc_event_exit(proc_event_base):
    fields = proc_event_base.fields + (
        ('process_pid', 'I'),
        ('process_tgid', 'I'),
        ('exit_code', 'I'),
        ('exit_signal', 'I'),
        ('parent_pid', 'I'),
        ('parent_tgid', 'I'),
    )


class proc_event_control(cn_msg):
    fields = cn_msg.fields + (('action', 'I'),)


class ProcEventMarshal(Marshal):
    key_format = 'I'
    key_offset = 36
    error_type = -1
    msg_map = {
        PROC_EVENT_NONE: proc_event_base,
        PROC_EVENT_FORK: proc_event_fork,
        PROC_EVENT_EXEC: proc_event_exec,
        PROC_EVENT_UID: proc_event_uid,
        PROC_EVENT_GID: proc_event_gid,
        PROC_EVENT_SID: proc_event_sid,
        PROC_EVENT_PTRACE: proc_event_ptrace,
        PROC_EVENT_COMM: proc_event_comm,
        PROC_EVENT_COREDUMP: proc_event_coredump,
        PROC_EVENT_EXIT: proc_event_exit,
    }


class ProcEventSocket(ConnectorSocket):
    def __init__(self, fileno=None):
        super().__init__(fileno=fileno)
        self.marshal = ProcEventMarshal()

    def bind(self):
        return super().bind(groups=CN_IDX_PROC)

    def control(self, listen):
        msg = proc_event_control()
        msg['action'] = (
            PROC_CN_MCAST_LISTEN if listen else PROC_CN_MCAST_IGNORE
        )
        msg['idx'] = CN_IDX_PROC
        msg['val'] = CN_VAL_PROC
        msg['len'] = 4  # FIXME payload length calculation
        msg_type = NLMSG_DONE
        self.put(msg, msg_type, msg_flags=0, msg_seq=0)
        return tuple(self.get(msg_seq=-1))
