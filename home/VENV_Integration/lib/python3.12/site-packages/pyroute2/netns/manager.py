import errno

from pyroute2 import netns
from pyroute2.inotify.inotify_fd import Inotify
from pyroute2.iproute.linux import IPRoute
from pyroute2.netlink.exceptions import NetlinkError, SkipInode
from pyroute2.netlink.rtnl import RTM_DELNETNS, RTM_NEWNETNS
from pyroute2.netlink.rtnl.nsinfmsg import nsinfmsg


class NetNSManager(Inotify):
    def __init__(self, libc=None, path=None, target='netns_manager'):
        path = set(path or [])
        super(NetNSManager, self).__init__(libc, path)
        if not self.path:
            for d in ['/var/run/netns', '/var/run/docker/netns']:
                try:
                    self.register_path(d)
                except OSError:
                    pass
        self.ipr = IPRoute(target=target)
        self.registry = {}
        self.update()
        self.target = target

    def update(self):
        self.ipr.netns_path = self.path
        for info in self.ipr.get_netns_info():
            self.registry[info.get_attr('NSINFO_PATH')] = info

    def get(self):
        for msg in super(NetNSManager, self).get():
            info = nsinfmsg()
            if msg is None:
                info['header']['error'] = NetlinkError(errno.ECONNRESET)
                info['header']['type'] = RTM_DELNETNS
                info['header']['target'] = self.target
                info['event'] = 'RTM_DELNETNS'
                yield info
                return
            path = '{path}/{name}'.format(**msg)
            info['header']['error'] = None
            info['header']['target'] = self.target
            if path not in self.registry:
                self.update()
            if path in self.registry:
                info.load(self.registry[path])
            else:
                info['attrs'] = [('NSINFO_PATH', path)]
            del info['value']
            if msg['mask'] & 0x200:
                info['header']['type'] = RTM_DELNETNS
                info['event'] = 'RTM_DELNETNS'
            elif not msg['mask'] & 0x100:
                continue
            yield info

    def close(self, code=None):
        self.ipr.close()
        super(NetNSManager, self).close()

    def create(self, path):
        netnspath = netns._get_netnspath(path)
        try:
            netns.create(netnspath, self.libc)
        except OSError as e:
            raise NetlinkError(e.errno)
        info = self.ipr._dump_one_ns(netnspath, set())
        info['header']['type'] = RTM_NEWNETNS
        info['header']['target'] = self.target
        info['event'] = 'RTM_NEWNETNS'
        del info['value']
        return (info,)

    def remove(self, path):
        netnspath = netns._get_netnspath(path)
        info = None
        try:
            info = self.ipr._dump_one_ns(netnspath, set())
        except SkipInode as e:
            raise NetlinkError(e.code)
        info['header']['type'] = RTM_DELNETNS
        info['header']['target'] = self.target
        info['event'] = 'RTM_DELNETNS'
        del info['value']
        try:
            netns.remove(netnspath, self.libc)
        except OSError as e:
            raise NetlinkError(e.errno)
        return (info,)

    def netns(self, cmd, *argv, **kwarg):
        path = kwarg.get('path', kwarg.get('NSINFO_PATH'))
        if path is None:
            raise ValueError('netns spec is required')
        netnspath = netns._get_netnspath(path)
        if cmd == 'add':
            return self.create(netnspath)
        elif cmd == 'del':
            return self.remove(netnspath)
        elif cmd not in ('get', 'set'):
            raise ValueError('method not supported')
        for item in self.dump():
            if item.get_attr('NSINFO_PATH') == netnspath:
                return (item,)
        return ()

    def dump(self, groups=None):
        return self.ipr.get_netns_info()
