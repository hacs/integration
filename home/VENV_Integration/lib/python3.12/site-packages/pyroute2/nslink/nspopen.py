'''
NSPopen
=======

The `NSPopen` class has nothing to do with netlink at
all, but it is required to have a reasonable network
namespace support.

'''

import atexit
import fcntl
import subprocess
import sys
import threading
import types

from pyroute2 import config
from pyroute2.common import file, metaclass
from pyroute2.netns import setns


def _handle(result):
    if result['code'] == 500:
        raise result['data']
    elif result['code'] == 200:
        return result['data']
    else:
        raise TypeError('unsupported return code')


def _make_fcntl(prime, target):
    def func(*argv, **kwarg):
        return target(prime.fileno(), *argv, **kwarg)

    return func


def _make_func(target):
    def func(*argv, **kwarg):
        return target(*argv, **kwarg)

    return func


def _make_property(name):
    def func(self):
        return getattr(self.prime, name)

    return property(func)


def _map_api(api, obj):
    for attr_name in dir(obj):
        attr = getattr(obj, attr_name)
        api[attr_name] = {'api': None}
        api[attr_name]['callable'] = hasattr(attr, '__call__')
        api[attr_name]['doc'] = (
            attr.__doc__ if hasattr(attr, '__doc__') else None
        )


class MetaPopen(type):
    '''
    API definition for NSPopen.

    All this stuff is required to make `help()` function happy.
    '''

    def __init__(cls, *argv, **kwarg):
        super(MetaPopen, cls).__init__(*argv, **kwarg)
        # copy docstrings and create proxy slots
        cls.api = {}
        _map_api(cls.api, subprocess.Popen)
        for fname in ('stdin', 'stdout', 'stderr'):
            m = {}
            cls.api[fname] = {'callable': False, 'api': m}
            _map_api(m, file)
            for ename in ('fcntl', 'ioctl', 'flock', 'lockf'):
                m[ename] = {
                    'api': None,
                    'callable': True,
                    'doc': getattr(fcntl, ename).__doc__,
                }

    def __dir__(cls):
        return list(cls.api.keys()) + ['release']

    def __getattribute__(cls, key):
        try:
            return type.__getattribute__(cls, key)
        except AttributeError:
            attr = getattr(subprocess.Popen, key)
            if isinstance(attr, (types.MethodType, types.FunctionType)):

                def proxy(*argv, **kwarg):
                    return attr(*argv, **kwarg)

                proxy.__doc__ = attr.__doc__
                proxy.__objclass__ = cls
                return proxy
            else:
                return attr


class NSPopenFile(object):
    def __init__(self, prime):
        self.prime = prime

        for aname in dir(prime):
            if aname.startswith('_'):
                continue

            target = getattr(prime, aname)
            if isinstance(target, (types.BuiltinMethodType, types.MethodType)):
                func = _make_func(target)
                func.__name__ = aname
                func.__doc__ = getattr(target, '__doc__', '')
                setattr(self, aname, func)
                del func
            else:
                setattr(self.__class__, aname, _make_property(aname))

        for fname in ('fcntl', 'ioctl', 'flock', 'lockf'):
            target = getattr(fcntl, fname)
            func = _make_fcntl(prime, target)
            func.__name__ = fname
            func.__doc__ = getattr(target, '__doc__', '')
            setattr(self, fname, func)
            del func


def NSPopenServer(nsname, flags, channel_in, channel_out, argv, kwarg):
    # set netns
    try:
        setns(nsname, flags=flags, libc=kwarg.pop('libc', None))
    except Exception as e:
        channel_out.put(e)
        return
    # create the Popen object
    child = subprocess.Popen(*argv, **kwarg)
    for fname in ['stdout', 'stderr', 'stdin']:
        obj = getattr(child, fname)
        if obj is not None:
            fproxy = NSPopenFile(obj)
            setattr(child, fname, fproxy)

    # send the API map
    channel_out.put(None)

    while True:
        # synchronous mode
        # 1. get the command from the API
        try:
            call = channel_in.get()
        except:
            (et, ev, tb) = sys.exc_info()
            try:
                channel_out.put({'code': 500, 'data': ev})
            except:
                pass
            break

        # 2. stop?
        if call['name'] == 'release':
            break

        # 3. run the call
        try:
            # get the object namespace
            ns = call.get('namespace')
            obj = child
            if ns:
                for step in ns.split('.'):
                    obj = getattr(obj, step)
            attr = getattr(obj, call['name'])
            if isinstance(
                attr,
                (
                    types.MethodType,
                    types.FunctionType,
                    types.BuiltinMethodType,
                ),
            ):
                result = attr(*call['argv'], **call['kwarg'])
            else:
                result = attr
            channel_out.put({'code': 200, 'data': result})
        except:
            (et, ev, tb) = sys.exc_info()
            channel_out.put({'code': 500, 'data': ev})
    child.wait()


class ObjNS(object):
    ns = None

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def __getattribute__(self, key):
        try:
            return object.__getattribute__(self, key)
        except AttributeError:
            with self.lock:
                if self.released:
                    raise RuntimeError('the object is released')

                if self.api.get(key) and self.api[key]['callable']:

                    def proxy(*argv, **kwarg):
                        self.channel_out.put(
                            {
                                'name': key,
                                'argv': argv,
                                'namespace': self.ns,
                                'kwarg': kwarg,
                            }
                        )
                        return _handle(self.channel_in.get())

                    if key in self.api:
                        proxy.__doc__ = self.api[key]['doc']
                    return proxy
                else:
                    if key in ('stdin', 'stdout', 'stderr'):
                        objns = ObjNS()
                        objns.ns = key
                        objns.api = self.api.get(key, {}).get('api', {})
                        objns.channel_out = self.channel_out
                        objns.channel_in = self.channel_in
                        objns.released = self.released
                        objns.lock = self.lock
                        return objns
                    else:
                        self.channel_out.put(
                            {'name': key, 'namespace': self.ns}
                        )
                        return _handle(self.channel_in.get())


@metaclass(MetaPopen)
class NSPopen(ObjNS):
    '''
    A proxy class to run `Popen()` object in some network namespace.

    Sample to run `ip ad` command in `nsname` network namespace::

        nsp = NSPopen('nsname', ['ip', 'ad'], stdout=subprocess.PIPE)
        print(nsp.communicate())
        nsp.wait()
        nsp.release()

    The `NSPopen` class was intended to be a drop-in replacement
    for the `Popen` class, but there are still some important
    differences.

    The `NSPopen` object implicitly spawns a child python process
    to be run in the background in a network namespace. The target
    process specified as the argument of the `NSPopen` will be
    started in its turn from this child. Thus all the fd numbers
    of the running `NSPopen` object are meaningless in the context
    of the main process. Trying to operate on them, one will get
    'Bad file descriptor' in the best case or a system call working
    on a wrong file descriptor in the worst case. A possible
    solution would be to transfer file descriptors between the
    `NSPopen` object and the main process, but it is not implemented
    yet.

    The process' diagram for `NSPopen('test', ['ip', 'ad'])`::

        +---------------------+     +--------------+     +------------+
        | main python process |<--->| child python |<--->| netns test |
        | NSPopen()           |     | Popen()      |     | $ ip ad    |
        +---------------------+     +--------------+     +------------+

    As a workaround for the issue with file descriptors, some
    additional methods are available on file objects `stdin`,
    `stdout` and `stderr`. E.g., one can run fcntl calls::

        from fcntl import F_GETFL
        from pyroute2 import NSPopen
        from subprocess import PIPE

        proc = NSPopen('test', ['my_program'], stdout=PIPE)
        flags = proc.stdout.fcntl(F_GETFL)

    In that way one can use `fcntl()`, `ioctl()`, `flock()` and
    `lockf()` calls.

    Another additional method is `release()`, which can be used to
    explicitly stop the proxy process and release all the resources.
    '''

    def __init__(self, nsname, *argv, **kwarg):
        '''
        The only differences from the `subprocess.Popen` init are:
        * `nsname` -- network namespace name
        * `flags` keyword argument

        All other arguments are passed directly to `subprocess.Popen`.

        Flags usage samples. Create a network namespace, if it doesn't
        exist yet::

            import os
            nsp = NSPopen('nsname', ['command'], flags=os.O_CREAT)

        Create a network namespace only if it doesn't exist, otherwise
        fail and raise an exception::

            import os
            nsp = NSPopen('nsname', ['command'], flags=os.O_CREAT | os.O_EXCL)
        '''
        # create a child
        self.nsname = nsname
        if 'flags' in kwarg:
            self.flags = kwarg.pop('flags')
        else:
            self.flags = 0
        self.channel_out = config.MpQueue()
        self.channel_in = config.MpQueue()
        self.lock = threading.Lock()
        self.released = False
        self.server = config.MpProcess(
            target=NSPopenServer,
            args=(
                self.nsname,
                self.flags,
                self.channel_out,
                self.channel_in,
                argv,
                kwarg,
            ),
        )
        # start the child and check the status
        self.server.start()
        response = self.channel_in.get()
        if isinstance(response, Exception):
            self.server.join()
            raise response
        else:
            atexit.register(self.release)

    def release(self):
        '''
        Explicitly stop the proxy process and release all the
        resources. The `NSPopen` object can not be used after
        the `release()` call.
        '''
        with self.lock:
            if self.released:
                return
            self.released = True
            self.channel_out.put({'name': 'release'})
            self.channel_out.close()
            self.channel_in.close()
            self.server.join()
            # clean leftover pipes that would be closed at program exit
            del self.server
            del self.channel_out
            del self.channel_in

    def __dir__(self):
        return list(self.api.keys()) + ['release']
