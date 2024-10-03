import os
import select
import threading

from pyroute2.netlink.rtnl import RTM_VALUES
from pyroute2.netlink.rtnl.riprsocket import RawIPRSocket


def sync(f):
    '''
    A decorator to wrap up external utility calls.

    A decorated function receives a netlink message
    as a parameter, and then:

    1. Starts a monitoring thread
    2. Performs the external call
    3. Waits for a netlink event specified by `msg`
    4. Joins the monitoring thread

    If the wrapped function raises an exception, the
    monitoring thread will be forced to stop via the
    control channel pipe. The exception will be then
    forwarded.
    '''

    def monitor(event, ifname, cmd):
        with RawIPRSocket() as ipr:
            poll = select.poll()
            poll.register(ipr, select.POLLIN | select.POLLPRI)
            poll.register(cmd, select.POLLIN | select.POLLPRI)
            ipr.bind()
            while True:
                events = poll.poll()
                for fd, event in events:
                    if fd == ipr.fileno():
                        msgs = ipr.get()
                        for msg in msgs:
                            if (
                                msg.get('event') == event
                                and msg.get_attr('IFLA_IFNAME') == ifname
                            ):
                                return
                    else:
                        return

    def decorated(msg):
        rcmd, cmd = os.pipe()
        t = threading.Thread(
            target=monitor,
            args=(
                RTM_VALUES[msg['header']['type']],
                msg.get_attr('IFLA_IFNAME'),
                rcmd,
            ),
        )
        t.start()
        ret = None
        try:
            ret = f(msg)
        except Exception:
            raise
        finally:
            os.write(cmd, b'q')
            t.join()
            os.close(rcmd)
            os.close(cmd)
        return ret

    return decorated
