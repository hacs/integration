'''
TaskStats module
================

All that you should know about TaskStats, is that you should not
use it. But if you have to, ok::

    import os
    from pyroute2 import TaskStats
    ts = TaskStats()
    ts.get_pid_stat(os.getpid())

It is not implemented normally yet, but some methods are already
usable.
'''

from pyroute2.netlink import NLM_F_REQUEST, genlmsg, nla, nla_struct
from pyroute2.netlink.generic import GenericNetlinkSocket

TASKSTATS_CMD_UNSPEC = 0  # Reserved
TASKSTATS_CMD_GET = 1  # user->kernel request/get-response
TASKSTATS_CMD_NEW = 2


class tcmd(genlmsg):
    nla_map = (
        ('TASKSTATS_CMD_ATTR_UNSPEC', 'none'),
        ('TASKSTATS_CMD_ATTR_PID', 'uint32'),
        ('TASKSTATS_CMD_ATTR_TGID', 'uint32'),
        ('TASKSTATS_CMD_ATTR_REGISTER_CPUMASK', 'asciiz'),
        ('TASKSTATS_CMD_ATTR_DEREGISTER_CPUMASK', 'asciiz'),
    )


class tstats(nla_struct):
    fields = (
        ('version', 'H'),  # 2
        ('ac_exitcode', 'I'),  # 4
        ('ac_flag', 'B'),  # 1
        ('ac_nice', 'B'),  # 1 --- 10
        ('cpu_count', 'Q'),  # 8
        ('cpu_delay_total', 'Q'),  # 8
        ('blkio_count', 'Q'),  # 8
        ('blkio_delay_total', 'Q'),  # 8
        ('swapin_count', 'Q'),  # 8
        ('swapin_delay_total', 'Q'),  # 8
        ('cpu_run_real_total', 'Q'),  # 8
        ('cpu_run_virtual_total', 'Q'),  # 8
        ('ac_comm', '32s'),  # 32 +++ 112
        ('ac_sched', 'B'),  # 1
        ('__ac_pad', '3x'),  # 3
        # (the ac_uid field is aligned(8), so we add more padding)
        ('__implicit_pad', '4x'),  # 4
        ('ac_uid', 'I'),  # 4  +++ 120
        ('ac_gid', 'I'),  # 4
        ('ac_pid', 'I'),  # 4
        ('ac_ppid', 'I'),  # 4
        ('ac_btime', 'I'),  # 4  +++ 136
        ('ac_etime', 'Q'),  # 8  +++ 144
        ('ac_utime', 'Q'),  # 8
        ('ac_stime', 'Q'),  # 8
        ('ac_minflt', 'Q'),  # 8
        ('ac_majflt', 'Q'),  # 8
        ('coremem', 'Q'),  # 8
        ('virtmem', 'Q'),  # 8
        ('hiwater_rss', 'Q'),  # 8
        ('hiwater_vm', 'Q'),  # 8
        ('read_char', 'Q'),  # 8
        ('write_char', 'Q'),  # 8
        ('read_syscalls', 'Q'),  # 8
        ('write_syscalls', 'Q'),  # 8
        ('read_bytes', 'Q'),  # ...
        ('write_bytes', 'Q'),
        ('cancelled_write_bytes', 'Q'),
        ('nvcsw', 'Q'),
        ('nivcsw', 'Q'),
        ('ac_utimescaled', 'Q'),
        ('ac_stimescaled', 'Q'),
        ('cpu_scaled_run_real_total', 'Q'),
    )

    def decode(self):
        nla_struct.decode(self)
        command = self['ac_comm']
        if isinstance(command, bytes):
            command = command.decode('utf-8')
        self['ac_comm'] = command[: command.find('\0')]


class taskstatsmsg(genlmsg):
    nla_map = (
        ('TASKSTATS_TYPE_UNSPEC', 'none'),
        ('TASKSTATS_TYPE_PID', 'uint32'),
        ('TASKSTATS_TYPE_TGID', 'uint32'),
        ('TASKSTATS_TYPE_STATS', 'stats'),
        ('TASKSTATS_TYPE_AGGR_PID', 'aggr_pid'),
        ('TASKSTATS_TYPE_AGGR_TGID', 'aggr_tgid'),
    )

    class stats(tstats):
        pass  # FIXME: optimize me!

    class aggr_id(nla):
        nla_map = (
            ('TASKSTATS_TYPE_UNSPEC', 'none'),
            ('TASKSTATS_TYPE_PID', 'uint32'),
            ('TASKSTATS_TYPE_TGID', 'uint32'),
            ('TASKSTATS_TYPE_STATS', 'stats'),
        )

        class stats(tstats):
            pass

    class aggr_pid(aggr_id):
        pass

    class aggr_tgid(aggr_id):
        pass


class TaskStats(GenericNetlinkSocket):
    def bind(self):
        GenericNetlinkSocket.bind(self, 'TASKSTATS', taskstatsmsg)

    def get_pid_stat(self, pid):
        '''
        Get taskstats for a process. Pid should be an integer.
        '''
        msg = tcmd()
        msg['cmd'] = TASKSTATS_CMD_GET
        msg['version'] = 1
        msg['attrs'].append(['TASKSTATS_CMD_ATTR_PID', pid])
        return self.nlm_request(msg, self.prid, msg_flags=NLM_F_REQUEST)

    def _register_mask(self, cmd, mask):
        msg = tcmd()
        msg['cmd'] = TASKSTATS_CMD_GET
        msg['version'] = 1
        msg['attrs'].append([cmd, mask])
        # there is no response to this request
        self.put(msg, self.prid, msg_flags=NLM_F_REQUEST)

    def register_mask(self, mask):
        '''
        Start the accounting for a processors by a mask. Mask is
        a string, e.g.::
            0,1 -- first two CPUs
            0-4,6-10 -- CPUs from 0 to 4 and from 6 to 10

        Though the kernel has a procedure, that cleans up accounting,
        when it is not used, it is recommended to run deregister_mask()
        before process exit.
        '''
        self._register_mask('TASKSTATS_CMD_ATTR_REGISTER_CPUMASK', mask)

    def deregister_mask(self, mask):
        '''
        Stop the accounting.
        '''
        self._register_mask('TASKSTATS_CMD_ATTR_DEREGISTER_CPUMASK', mask)
