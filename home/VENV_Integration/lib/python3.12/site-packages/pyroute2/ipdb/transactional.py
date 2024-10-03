'''
'''

import logging
import threading

from pyroute2.common import Dotkeys, uuid32
from pyroute2.ipdb.exceptions import CommitException
from pyroute2.ipdb.linkedset import LinkedSet

# How long should we wait on EACH commit() checkpoint: for ipaddr,
# ports etc. That's not total commit() timeout.
SYNC_TIMEOUT = 5
log = logging.getLogger(__name__)


class State(object):
    def __init__(self, lock=None):
        self.lock = lock or threading.Lock()
        self.flag = 0

    def acquire(self):
        self.lock.acquire()
        self.flag += 1

    def release(self):
        if self.flag < 1:
            raise RuntimeError('release unlocked state')
        self.flag -= 1
        self.lock.release()

    def is_set(self):
        return self.flag

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()


def update(f):
    def decorated(self, *argv, **kwarg):
        if self._mode == 'snapshot':
            # short-circuit
            with self._write_lock:
                return f(self, True, *argv, **kwarg)
        elif self._mode == 'readonly':
            raise RuntimeError('can not change readonly object')

        with self._write_lock:
            direct = self._direct_state.is_set()
            if not direct:
                # 1. 'implicit': begin transaction, if there is none
                if self._mode == 'implicit':
                    if not self.current_tx:
                        self.begin()
                # 2. require open transaction for 'explicit' type
                elif self._mode == 'explicit':
                    if not self.current_tx:
                        raise TypeError('start a transaction first')
                # do not support other modes
                else:
                    raise TypeError('transaction mode not supported')
                # now that the transaction _is_ open
            return f(self, direct, *argv, **kwarg)

    decorated.__doc__ = f.__doc__
    return decorated


def with_transaction(f):
    def decorated(self, direct, *argv, **kwarg):
        if direct:
            f(self, *argv, **kwarg)
        else:
            transaction = self.current_tx
            f(transaction, *argv, **kwarg)
        return self

    return update(decorated)


class Transactional(Dotkeys):
    '''
    Utility class that implements common transactional logic.
    '''

    _fields = []
    _virtual_fields = []
    _fields_cmp = {}
    _linked_sets = []
    _nested = []

    def __init__(self, ipdb=None, mode=None, parent=None, uid=None):
        #
        if ipdb is not None:
            self.nl = ipdb.nl
            self.ipdb = ipdb
        else:
            self.nl = None
            self.ipdb = None
        #
        self._parent = None
        if parent is not None:
            self._mode = mode or parent._mode
            self._parent = parent
        elif ipdb is not None:
            self._mode = mode or ipdb.mode
        else:
            self._mode = mode or 'implicit'
        #
        self.nlmsg = None
        self.uid = uid or uuid32()
        self.last_error = None
        self._commit_hooks = []
        self._sids = []
        self._ts = threading.local()
        self._snapshots = {}
        self.global_tx = {}
        self._targets = {}
        self._local_targets = {}
        self._write_lock = threading.RLock()
        self._direct_state = State(self._write_lock)
        self._linked_sets = self._linked_sets or set()
        #
        for i in self._fields:
            Dotkeys.__setitem__(self, i, None)

    @property
    def ro(self):
        return self.pick(detached=False, readonly=True)

    def register_commit_hook(self, hook):
        ''' '''
        self._commit_hooks.append(hook)

    def unregister_commit_hook(self, hook):
        ''' '''
        with self._write_lock:
            for cb in tuple(self._commit_hooks):
                if hook == cb:
                    self._commit_hooks.pop(self._commit_hooks.index(cb))

    ##
    # Object serialization: dump, pick
    def dump(self, not_none=True):
        ''' '''
        with self._write_lock:
            res = {}
            for key in self:
                if self[key] is not None and key[0] != '_':
                    if isinstance(self[key], Transactional):
                        res[key] = self[key].dump()
                    elif isinstance(self[key], LinkedSet):
                        res[key] = tuple(self[key])
                    else:
                        res[key] = self[key]
            return res

    def pick(self, detached=True, uid=None, parent=None, readonly=False):
        '''
        Get a snapshot of the object. Can be of two
        types:
        * detached=True -- (default) "true" snapshot
        * detached=False -- keep ip addr set updated from OS

        Please note, that "updated" doesn't mean "in sync".
        The reason behind this logic is that snapshots can be
        used as transactions.
        '''
        with self._write_lock:
            res = self.__class__(
                ipdb=self.ipdb, mode='snapshot', parent=parent, uid=uid
            )
            for key, value in self.items():
                if self[key] is not None:
                    if key in self._fields:
                        res[key] = self[key]
            for key in self._linked_sets:
                res[key] = type(self[key])(self[key])
                if not detached:
                    self[key].connect(res[key])
            if readonly:
                res._mode = 'readonly'

            return res

    ##
    # Context management: enter, exit
    def __enter__(self):
        if self._mode == 'readonly':
            return self
        elif self._mode not in ('implicit', 'explicit'):
            raise TypeError('context managers require a transactional mode')
        if not self.current_tx:
            self.begin()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # apply transaction only if there was no error
        if self._mode == 'readonly':
            return
        elif exc_type is None:
            try:
                self.commit()
            except Exception as e:
                self.last_error = e
                raise

    ##
    # Implicit object transfomations
    def __repr__(self):
        res = {}
        for i in tuple(self):
            if self[i] is not None:
                res[i] = self[i]
        return res.__repr__()

    ##
    # Object ops: +, -, /, ...
    def __sub__(self, vs):
        # create result
        res = {}

        with self._direct_state:
            # simple keys
            for key in self:
                if key in self._fields:
                    if (key not in vs) or (self[key] != vs[key]):
                        res[key] = self[key]
        for key in self._linked_sets:
            diff = type(self[key])(self[key] - vs[key])
            if diff:
                res[key] = diff
            else:
                res[key] = set()
        for key in self._nested:
            res[key] = self[key] - vs[key]
        return res

    def __floordiv__(self, vs):
        left = {}
        right = {}
        with self._direct_state:
            with vs._direct_state:
                for key in set(tuple(self.keys()) + tuple(vs.keys())):
                    if self.get(key, None) != vs.get(key, None):
                        left[key] = self.get(key)
                        right[key] = vs.get(key)
                        continue
                    if key not in self:
                        right[key] = vs[key]
                    elif key not in vs:
                        left[key] = self[key]
        for key in self._linked_sets:
            ldiff = type(self[key])(self[key] - vs[key])
            rdiff = type(vs[key])(vs[key] - self[key])
            if ldiff:
                left[key] = ldiff
            else:
                left[key] = set()
            if rdiff:
                right[key] = rdiff
            else:
                right[key] = set()
        for key in self._nested:
            left[key], right[key] = self[key] // vs[key]
        return left, right

    ##
    # Methods to be overloaded
    def detach(self):
        pass

    def load(self, data):
        pass

    def commit(self, *args, **kwarg):
        pass

    def last_snapshot_id(self):
        return self._sids[-1]

    def invalidate(self):
        # on failure, invalidate the interface and detach it
        # from the parent
        # 0. obtain lock on IPDB, to avoid deadlocks
        # ... all the DB updates will wait
        with self.ipdb.exclusive:
            # 1. drop the IPRoute() link
            self.nl = None
            # 2. clean up ipdb
            self.detach()
            # 3. invalidate the interface
            with self._direct_state:
                for i in tuple(self.keys()):
                    del self[i]
                self['ipdb_scope'] = 'invalid'
            # 4. the rest
            self._mode = 'invalid'

    ##
    # Snapshot methods
    def revert(self, sid):
        with self._write_lock:
            assert sid in self._snapshots
            self.local_tx[sid] = self._snapshots[sid]
            self.global_tx[sid] = self._snapshots[sid]
            self.current_tx = self._snapshots[sid]
            self._sids.remove(sid)
            del self._snapshots[sid]
            return self

    def snapshot(self, sid=None):
        '''
        Create new snapshot
        '''
        if self._parent:
            raise RuntimeError("Can't init snapshot from a nested object")
        if (self.ipdb is not None) and self.ipdb._stop:
            raise RuntimeError("Can't create snapshots on released IPDB")
        t = self.pick(detached=True, uid=sid)
        self._snapshots[t.uid] = t
        self._sids.append(t.uid)
        for key, value in t.items():
            if isinstance(value, Transactional):
                value.snapshot(sid=t.uid)
        return t.uid

    def last_snapshot(self):
        if not self._sids:
            raise TypeError('create a snapshot first')
        return self._snapshots[self._sids[-1]]

    ##
    # Current tx
    def _set_current_tx(self, tx):
        with self._write_lock:
            self._ts.current = tx

    def _get_current_tx(self):
        '''
        The current active transaction (thread-local)
        '''
        with self._write_lock:
            if not hasattr(self._ts, 'current'):
                self._ts.current = None
            return self._ts.current

    current_tx = property(_get_current_tx, _set_current_tx)

    ##
    # Local tx registry
    def _get_local_tx(self):
        with self._write_lock:
            if not hasattr(self._ts, 'tx'):
                self._ts.tx = {}
            return self._ts.tx

    local_tx = property(_get_local_tx)

    ##
    # Transaction ops: begin, review, drop
    def begin(self):
        '''
        Start new transaction
        '''
        if self._parent is not None:
            self._parent.begin()
        else:
            return self._begin()

    def _begin(self, tid=None):
        if (self.ipdb is not None) and self.ipdb._stop:
            raise RuntimeError("Can't start transaction on released IPDB")
        t = self.pick(detached=False, uid=tid)
        self.local_tx[t.uid] = t
        self.global_tx[t.uid] = t
        if self.current_tx is None:
            self.current_tx = t
        for key, value in t.items():
            if isinstance(value, Transactional):
                # start transaction on a nested object
                value._begin(tid=t.uid)
                # link transaction to own one
                t[key] = value.global_tx[t.uid]
        return t.uid

    def review(self, tid=None):
        '''
        Review the changes made in the transaction `tid`
        or in the current active transaction (thread-local)
        '''
        if self.current_tx is None:
            raise TypeError('start a transaction first')

        tid = tid or self.current_tx.uid

        if self.get('ipdb_scope') == 'create':
            if self.current_tx is not None:
                prime = self.current_tx
            else:
                log.warning('the "create" scope without transaction')
                prime = self
            return dict(
                [(x[0], x[1]) for x in prime.items() if x[1] is not None]
            )

        with self._write_lock:
            added = self.global_tx[tid] - self
            removed = self - self.global_tx[tid]
            for key in self._linked_sets:
                added['-%s' % (key)] = removed[key]
                added['+%s' % (key)] = added[key]
                del added[key]
            return added

    def drop(self, tid=None):
        '''
        Drop a transaction. If tid is not specified, drop
        the current one.
        '''
        with self._write_lock:
            if tid is None:
                tx = self.current_tx
                if tx is None:
                    raise TypeError("no transaction")
            else:
                tx = self.global_tx[tid]

            if self.current_tx == tx:
                self.current_tx = None

            # detach linked sets
            for key in self._linked_sets:
                if tx[key] in self[key].links:
                    self[key].disconnect(tx[key])
            for key, value in self.items():
                if isinstance(value, Transactional):
                    try:
                        value.drop(tx.uid)
                    except KeyError:
                        pass
            # finally -- delete the transaction
            del self.local_tx[tx.uid]
            del self.global_tx[tx.uid]

    ##
    # Property ops: set/get/delete
    @update
    def __setitem__(self, direct, key, value):
        if not direct:
            if self.get(key) == value:
                return
            # automatically set target on the active transaction,
            # which must be started prior to that call
            transaction = self.current_tx
            transaction[key] = value
            if value is not None:
                transaction._targets[key] = threading.Event()
        else:
            # set the item
            Dotkeys.__setitem__(self, key, value)

            # update on local targets
            with self._write_lock:
                if key in self._local_targets:
                    func = self._fields_cmp.get(key, lambda x, y: x == y)
                    if func(value, self._local_targets[key].value):
                        self._local_targets[key].set()

            # cascade update on nested targets
            for tn in tuple(self.global_tx.values()):
                if (key in tn._targets) and (key in tn):
                    if self._fields_cmp.get(key, lambda x, y: x == y)(
                        value, tn[key]
                    ):
                        tn._targets[key].set()

    @update
    def __delitem__(self, direct, key):
        # firstly set targets
        self[key] = None

        # then continue with delete
        if not direct:
            transaction = self.current_tx
            if key in transaction:
                del transaction[key]
        else:
            Dotkeys.__delitem__(self, key)

    def option(self, key, value):
        self[key] = value
        return self

    def unset(self, key):
        del self[key]
        return self

    def wait_all_targets(self):
        for key, target in self._targets.items():
            if key not in self._virtual_fields:
                target.wait(SYNC_TIMEOUT)
                if not target.is_set():
                    raise CommitException('target %s is not set' % key)

    def wait_target(self, key, timeout=SYNC_TIMEOUT):
        self._local_targets[key].wait(SYNC_TIMEOUT)
        with self._write_lock:
            return self._local_targets.pop(key).is_set()

    def set_target(self, key, value):
        with self._write_lock:
            self._local_targets[key] = threading.Event()
            self._local_targets[key].value = value
            if self.get(key) == value:
                self._local_targets[key].set()
            return self

    def mirror_target(self, key_from, key_to):
        with self._write_lock:
            self._local_targets[key_to] = self._local_targets[key_from]
            return self

    def set(self, key, value):
        self[key] = value
        return self
