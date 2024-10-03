'''

One object
----------

All the changes done using one object are applied in the order defined by
the corresponding object class.

.. code-block:: python

    eth0 = ndb.interfaces["eth0"]
    eth0.add_ip(address="10.0.0.1", prefixlen=24)
    eth0.set(state="up")
    eth0.set(mtu=1400)
    eth0.commit()

In the example above first the interface attributes like state, mtu, ifname
etc. will be applied, and only then IP addresses, bridge ports and like that,
regardless the order they are referenced before the `commit()` call.

The order is ok for most of cases. But if not, one can control it by calling
`commit()` in the required places, breaking one transaction into several
sequential transactions.

And since RTNL object methods return the object itself, it is possible to
write chains with multiple `commit()`:

.. code-block:: python

    (
        ndb.interfaces
        .create(ifname="test", kind="dummy")
        .add_ip(address="10.0.0.1", prefixlen=24)
        .commit()
        .set(state="up")
        .commit()
    )

Here the order is forced by explicit commits.

Multiple objects
----------------

An important functionality of NDB are rollbacks. And there is a way to batch
changes on multiple objects so one failure will trigger rollback of all the
changes on all the objects.

.. code-block:: python

    ctx = ndb.begin()
    ctx.push(
        # first set up a bridge
        (
            ndb.interfaces
            .create(ifname="br0", kind="bridge")
            .add_port("eth0")
            .add_port("eth1")
            .set(state="up")
            .add_ip("10.0.0.2/24")
        ),
        # and only then create a route
        (
            ndb.routes
            .create(
                dst="192.168.0.0",
                dst_len=24,
                gateway="10.0.0.1"
            )
        )
    )
    ctx.commit()  # if something goes wrong, the whole batch will be reverted


Ping a remote host
------------------

The simplest usecase for external checks is to test if a remote IP is still
reachable after the changes are applied:

.. code-block:: python

    from pyroute2.ndb.transaction import PingAddress

    ctx = ndb.begin()
    ctx.push(
        ndb.routes.create(dst="10.0.0.0", dst_len=24, gateway="172.16.0.1"),
        PingAddress("10.0.0.1")
    )
    ctx.commit()  # the route will be removed if ping fails

Or on the contrary, don't run transaction if a remote IP is reachable:

.. code-block:: python

    from pyroute2.ndb.transaction import Not, PingAddress

    ctx = ndb.begin()
    ctx.push(
        Not(PingAddress("10.0.0.1")),
        ndb.routes.create(dst="10.0.0.0", dst_len=24, gateway="172.16.0.1")
    )
    try:
        ctx.commit()
    except CheckProcessException:
        pass

In this example, the route will be added only if `10.0.0.1` is not reachable.

The default ping timeout is set to 1, but it is possible to customize it:

.. code-block:: python

    PingAddress("10.0.0.1", timeout=10)

Check an external processes
---------------------------

A more generic type of check is CheckProcess:

.. code-block:: python

    from pyroute2.ndb.transaction import CheckProcess

    with ndb.begin() as ctx:
        ctx.push(ndb.routes.create(
            dst="10.0.0.0",
            dst_len=24,
            gateway="172.16.0.1"
        ))
        ctx.push(CheckProcess('/path/to/script.sh'))
        #
        # --> <-- the route will be removed if the script fails

`CheckProcess` is `subprocess.Popen` based, is not a shell call, thus no pipes
or other shell syntax are allowed.

`CheckProcess` also accepts `timeout` argument:

.. code-block:: python

    CheckProcess('/path/to/script.sh', timeout=10).commit()

If the subprocess doens't finish within the timeout, it will be terminated
with SIGTERM. SIGKILL is not used.

Logging and debug
-----------------

`CheckProcess` and `PingAddress` accept log as an argument:

.. code-block:: python

    PingAddress("10.0.0.1", log=ndb.log.channel("util")).commit()
    CheckProcess("/path/to/script.sh", log=ndb.log.channel("util")).commit()

The check objects are thread safe and reusable, it is possible to run
`commit()` on them multiple times. The subprocess' stdout and stderr will
be both logged and saved:

.. code-block:: python

    check = CheckProcess("/path/to/script.sh")
    while True:
        check.commit()  # periodic check, the loop breaks on failure
        print(f'stdout: {check.out}')
        print(f'stderr: {check.err}')
        print(f'return code: {check.return_code}')
        time.sleep(10)

Check negation
--------------

It is possible to negate the check for `CheckProcess` and child classes

.. code-block:: python

    from pyroute2.ndb.transaction import Not, CheckProcess

    check = Not(CheckProcess('/path/to/script.sh'))
    check.commit()

API
---

'''

import logging
import shlex
import shutil
import subprocess
import threading

global_log = logging.getLogger(__name__)


class CheckProcessException(Exception):
    pass


class CheckProcess:
    '''
    Run an external process on `commit()` and raise `CheckProcessException`
    if the return code is not 0.

    Objects of this class are thread safe and reusable.
    '''

    def __init__(self, command, log=None, timeout=None):
        if not isinstance(command, str):
            raise TypeError('command must be a non empty string')
        if not len(command) > 0:
            raise TypeError('command must be a non empty string')
        self.log = log or global_log
        self.command = command
        self.args = shlex.split(command)
        self.timeout = timeout
        self.return_code = None
        self.out = None
        self.err = None
        self.lock = threading.Lock()

    def commit(self):
        with self.lock:
            self.args[0] = shutil.which(self.args[0])
            if self.args[0] is None:
                raise FileNotFoundError()
            process = subprocess.Popen(
                self.args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            try:
                self.log.debug(f'process check {self.args}')
                self.out, self.err = process.communicate(timeout=self.timeout)
                self.log.debug(f'process output: {self.out}')
                self.log.debug(f'process stderr: {self.err}')
            except subprocess.TimeoutExpired:
                self.log.debug('process timeout expired')
                process.terminate()
                process.stdout.close()
                process.stderr.close()
            finally:
                self.return_code = process.wait()
            if self.return_code != 0:
                raise CheckProcessException('CheckProcess failed')

    def rollback(self):
        pass

    def __repr__(self):
        return f'[{self.command}]'


class PingAddress(CheckProcess):
    def __init__(self, address, log=None, timeout=1):
        super(PingAddress, self).__init__(
            f'ping -c 1 -W {timeout} {address}', log=log
        )


class Not:
    '''
    Negate the `CheckProcess` results. If `CheckProcess.commit()` succeeds,
    raise CheckProcessException, and vice versa, if `CheckProcess.commit()`
    fails, return success.
    '''

    def __init__(self, transaction):
        self.tx = transaction

    def commit(self):
        success = True
        try:
            self.tx.commit()
        except Exception:
            success = False
        if success:
            raise CheckProcessException(f'{self.tx} succeeded')

    def rollback(self):
        pass


class Transaction:
    '''
    `Transaction` class is an independent utility class. Being designed to
    be used with NDB object transactions, it may be used with any object
    implementing commit/rollback protocol, see `commit()` method.

    The class supports the context manager protocol and `Transaction` objects
    may be used in `with` statements:

    .. code-block:: python

        with Transaction() as tx:
            tx.push(obj0)  # enqueue objects
            tx.push(obj1)
            # --> <-- run commit() for every object in self.queue
            #
            # if any commit() fails, run rollback() for every
            # executed commit() in the reverse order

    NDB provides a utility method to create `Transaction` objects:

    .. code-block:: python

        with ndb.begin() as tx:
            tx.push(ndb.interfaces["eth0"].set(state="up"))
            tx.push(ndb.interfaces["eth1"].set(state="up"))
    '''

    def __init__(self, log=None):
        self.queue = []
        self.event = threading.Event()
        self.event.clear()
        self.log = global_log or log
        self.log.debug('begin transaction')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.commit()

    def push(self, *argv):
        '''
        Push objects to the transaction queue. One may use any number
        of positional arguments:

        .. code-block:: python

            tx.push(obj0)
            tx.push(obj0, obj1, obj2)
            tx.push(*[obj0, obj1, obj2])
        '''
        for obj in argv:
            self.log.debug('queue %s' % type(obj))
            self.queue.append(obj)
        return self

    def append(self, obj):
        '''
        Append one object to the queue.
        '''
        self.log.debug('queue %s' % type(obj))
        self.push(obj)
        return self

    def pop(self, index=-1):
        '''
        Pop an object from the queue. If an index is not specified,
        pop the last (the rightmost) object.
        '''
        self.log.debug('pop %s' % index)
        self.queue.pop(index)
        return self

    def insert(self, index, obj):
        '''
        Insert an object into the queue. The position index is required.
        '''
        self.log.debug('insert %i %s' % (index, type(obj)))
        self.queue.insert(index, obj)
        return self

    def cancel(self):
        '''
        Cancel the transaction and empty the queue.
        '''
        self.log.debug('cancel transaction')
        self.queue = []
        return self

    def wait(self, timeout=None):
        '''
        Wait until the transaction to be successfully committed.
        '''
        return self.event.wait(timeout)

    def done(self):
        '''
        Check if the done event is set.
        '''
        return self.event.is_set()

    def commit(self):
        '''
        Execute `commit()` for every queued object. If an execution
        fails, execute `rollback()` for every executed commit. All
        objects in the queue that follows the failed one will remain
        intact.

        Raises the original exception of the failed `commit()`. All
        the `rollback()` exceptions are ignored.
        '''
        self.log.debug('commit')
        rollbacks = []
        for obj in self.queue:
            rollbacks.append(obj)
            try:
                obj.commit()
            except Exception:
                for rb in reversed(rollbacks):
                    try:
                        rb.rollback()
                    except Exception as e:
                        self.log.warning('ignore rollback exception: %s' % e)
                raise
        self.event.set()
        return self
