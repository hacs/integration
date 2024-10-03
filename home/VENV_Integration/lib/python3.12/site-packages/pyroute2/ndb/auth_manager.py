'''

AAA concept
-----------

AAA refers to Authentication, Authorization and Accounting. NDB provides
a minimalistic API to integrate Authorization routines, leaving the
rest -- Authentication and Accounting -- to the user.

Some of NDB routines and RTNL object methods are guarded with a
parametrized decorator. The decorator takes the only parameter `tag`::

    @check_auth('obj:read')
    def __getitem__(self, key):
        ...

    @check_auth('obj:modify')
    def __setitem__(self, key, value):
        ...

AuthManager
-----------

The tag is checked by `AuthManager.check(...)` routine. The routine is
the only method that must be provided by AuthManager-compatible objects,
and must be defined as::

    def check(self, obj, tag):
        # -> True: grant access to the tag
        # -> False: reject access
        # -> raise Exception(): reject access with a specific exception
        ...

NDB module provides an example AuthManager::

    from pyroute2 import NDB
    from pyroute2.ndb.auth_manager import AuthManager

    ndb = NDB(log='debug')

    am = AuthManager({'obj:list': False,    # deny dump(), summary()
                      'obj:read': True,     # permit reading RTNL attributes
                      'obj:modify': True},  # permit add_ip(), commit() etc.
                     ndb.log.channel('auth'))

    ap = ndb.auth_proxy(am)
    ap.interfaces.summary()  # <-- fails with PermissionError

You can implement custom AuthManager classes, the only requirement -- they
must provide `.check(self, obj, tag)` routine, which returns `True` or
`False` or raises an exception.

'''


class check_auth(object):
    def __init__(self, tag):
        self.tag = tag

    def __call__(self, f):
        def guard(obj, *argv, **kwarg):
            if not getattr(obj, '_init_complete', True):
                return f(obj, *argv, **kwarg)
            if not obj.auth_managers:
                raise PermissionError('access rejected')
            if all([x.check(obj, self.tag) for x in obj.auth_managers]):
                return f(obj, *argv, **kwarg)
            raise PermissionError('access rejected')

        guard.__doc__ = f.__doc__
        return guard


class AuthManager(object):
    def __init__(self, auth, log, policy=False):
        self.auth = auth
        self.log = log
        self.policy = policy
        self.exception = PermissionError

    def check(self, obj, tag):
        ret = self.policy
        if isinstance(self.auth, dict):
            ret = self.auth.get(tag, self.policy)
        if not ret and self.exception:
            raise self.exception('%s access rejected' % (tag,))
        return ret
