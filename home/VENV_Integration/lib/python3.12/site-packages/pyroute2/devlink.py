import logging

from pyroute2.netlink import NLM_F_DUMP, NLM_F_REQUEST
from pyroute2.netlink.devlink import DEVLINK_NAMES, DevlinkSocket, devlinkcmd

log = logging.getLogger(__name__)


class DL(DevlinkSocket):
    def __init__(self, *argv, **kwarg):
        # get specific groups kwarg
        if 'groups' in kwarg:
            groups = kwarg['groups']
            del kwarg['groups']
        else:
            groups = None

        # get specific async kwarg
        if 'async' in kwarg:
            # FIXME
            # raise deprecation error after 0.5.3
            #
            log.warning(
                'use "async_cache" instead of "async", '
                '"async" is a keyword from Python 3.7'
            )
            kwarg['async_cache'] = kwarg.pop('async')

        if 'async_cache' in kwarg:
            async_cache = kwarg.pop('async_cache')
        else:
            async_cache = False

        # align groups with async_cache
        if groups is None:
            groups = ~0 if async_cache else 0

        # continue with init
        super(DL, self).__init__(*argv, **kwarg)

        # do automatic bind
        # FIXME: unfortunately we can not omit it here
        try:
            self.bind(groups, async_cache=async_cache)
        except:
            # thanks to jtluka at redhat.com and the LNST
            # team for the fixed fd leak
            super(DL, self).close()
            raise

    def list(self):
        return self.get_dump()

    def get_dump(self):
        msg = devlinkcmd()
        msg['cmd'] = DEVLINK_NAMES['DEVLINK_CMD_GET']
        return tuple(
            self.nlm_request(
                msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_DUMP
            )
        )

    def port_list(self):
        return self.get_port_dump()

    def get_port_dump(self):
        msg = devlinkcmd()
        msg['cmd'] = DEVLINK_NAMES['DEVLINK_CMD_PORT_GET']
        return tuple(
            self.nlm_request(
                msg, msg_type=self.prid, msg_flags=NLM_F_REQUEST | NLM_F_DUMP
            )
        )
