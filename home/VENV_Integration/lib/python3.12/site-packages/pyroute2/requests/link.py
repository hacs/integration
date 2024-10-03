from pyroute2.netlink.rtnl.ifinfmsg import IFF_NOARP, ifinfmsg
from pyroute2.netlink.rtnl.ifinfmsg.plugins.vlan import flags as vlan_flags

from .common import Index, IPRouteFilter, NLAKeyTransform


class LinkFieldFilter(Index, NLAKeyTransform):
    _nla_prefix = 'IFLA_'

    def _link(self, key, context, value):
        if isinstance(value, dict):
            return {key: value['index']}
        return {key: value}

    def set_vxlan_link(self, context, value):
        return self._link('vxlan_link', context, value)

    def set_link(self, context, value):
        return self._link('link', context, value)

    def set_master(self, context, value):
        return self._link('master', context, value)

    def set_address(self, context, value):
        if isinstance(value, str):
            # lower the case
            if not value.islower():
                value = value.lower()
            # convert xxxx.xxxx.xxxx to xx:xx:xx:xx:xx:xx
            if len(value) == 14 and value[4] == value[9] == '.':
                value = ':'.join(
                    [':'.join((x[:2], x[2:])) for x in value.split('.')]
                )
        return {'address': value}

    def set_carrier(self, context, value):
        return {}

    def set_carrier_changes(self, context, value):
        return {}

    def set_info_slave_kind(self, context, value):
        return {}

    def set_mask(self, context, value):
        return {'change': value}

    def set_info_kind(self, context, value):
        return {'kind': value}


class LinkIPRouteFilter(IPRouteFilter):
    def set_altname(self, context, value):
        if self.command in ('property_add', 'property_del'):
            if not isinstance(value, (list, tuple, set)):
                value = [value]
            return {
                'IFLA_PROP_LIST': {
                    'attrs': [
                        ('IFLA_ALT_IFNAME', alt_ifname) for alt_ifname in value
                    ]
                }
            }
        else:
            return {'IFLA_ALT_IFNAME': value}

    def set_xdp_fd(self, context, value):
        return {'xdp': {'attrs': [('IFLA_XDP_FD', value)]}}

    def set_vf(self, context, value):
        return {'IFLA_VFINFO_LIST': self.get_vf(value)}

    def set_state(self, context, value):
        ret = {}
        if self.command == 'dump':
            return {'state': value}
        if value == 'up':
            ret['flags'] = context.get('flags', 0) or 0 | 1
        ret['change'] = context.get('change', 0) or 0 | 1
        return ret

    def set_arp(self, context, value):
        ret = {}
        if not value:
            ret['flags'] = context.get('flags', 0) or 0 | IFF_NOARP
        ret['change'] = context.get('change', 0) or 0 | IFF_NOARP
        return ret

    def set_noarp(self, context, value):
        ret = {}
        if value:
            ret['flags'] = context.get('flags', 0) or 0 | IFF_NOARP
        ret['change'] = context.get('change', 0) or 0 | IFF_NOARP
        return ret

    def finalize(self, context):
        # set interface type specific attributes
        self.kind = context.pop('kind', None)
        if self.kind is None:
            return
        # load specific NLA names
        self.specific = {}
        cls = ifinfmsg.ifinfo.data_map.get(self.kind, None)
        if cls is not None:
            prefix = cls.prefix or 'IFLA_'
            for nla, _ in cls.nla_map:
                self.specific[nla] = nla
                self.specific[nla[len(prefix) :].lower()] = nla

        if self.command == 'dump':
            context[('linkinfo', 'kind')] = self.kind
            for key, value in tuple(context.items()):
                if key in self.specific:
                    context[('linkinfo', 'data', key)] = value
                    try:
                        del context[key]
                    except KeyError:
                        pass
            return

        # get common ifinfmsg NLAs
        self.common = []
        for key, _ in ifinfmsg.nla_map:
            self.common.append(key)
            self.common.append(key[len(ifinfmsg.prefix) :].lower())
        self.common.append('family')
        self.common.append('ifi_type')
        self.common.append('index')
        self.common.append('flags')
        self.common.append('change')
        for key in ('index', 'change', 'flags'):
            if key not in context:
                context[key] = 0

        linkinfo = {'attrs': []}
        self.linkinfo = linkinfo['attrs']
        self._info_data = None
        self._info_slave_data = None
        context['IFLA_LINKINFO'] = linkinfo
        self.linkinfo.append(['IFLA_INFO_KIND', self.kind])
        # flush deferred NLAs
        for key, value in tuple(context.items()):
            if self.push_specific(key, value):
                try:
                    del context[key]
                except KeyError:
                    pass

    def push_specific(self, key, value):
        # FIXME: vlan hack
        if self.kind == 'vlan':
            if key == 'vlan_flags':
                if isinstance(value, (list, tuple)):
                    if len(value) == 2 and all(
                        (isinstance(x, int) for x in value)
                    ):
                        value = {'flags': value[0], 'mask': value[1]}
                    else:
                        ret = 0
                        for x in value:
                            ret |= vlan_flags.get(x, 1)
                        value = {'flags': ret, 'mask': ret}
                elif isinstance(value, int):
                    value = {'flags': value, 'mask': value}
                elif isinstance(value, str):
                    value = vlan_flags.get(value, 1)
                    value = {'flags': value, 'mask': value}
                elif not isinstance(value, dict):
                    raise ValueError()
            elif key in ('vlan_egress_qos', 'vlan_ingress_qos'):
                if isinstance(value, dict) and {'from', 'to'} == value.keys():
                    value = {'attrs': (('IFLA_VLAN_QOS_MAPPING', value),)}
        # the kind is known: lookup the NLA
        if key in self.specific:
            # FIXME: slave hack
            if self.kind.endswith('_slave'):
                self.info_slave_data.append((self.specific[key], value))
            else:
                self.info_data.append((self.specific[key], value))
            return True
        elif key == 'peer' and self.kind == 'veth':
            # FIXME: veth hack
            if isinstance(value, dict):
                attrs = []
                for k, v in value.items():
                    attrs.append([ifinfmsg.name2nla(k), v])
            else:
                attrs = [['IFLA_IFNAME', value]]
            nla = ['VETH_INFO_PEER', {'attrs': attrs}]
            self.info_data.append(nla)
            return True
        elif key == 'mode':
            # FIXME: ipvlan / tuntap / bond hack
            if self.kind == 'tuntap':
                nla = ['IFTUN_MODE', value]
            else:
                nla = ['IFLA_%s_MODE' % self.kind.upper(), value]
            self.info_data.append(nla)
            return True

        return False

    @property
    def info_data(self):
        if self._info_data is None:
            info_data = ('IFLA_INFO_DATA', {'attrs': []})
            self._info_data = info_data[1]['attrs']
            self.linkinfo.append(info_data)
        return self._info_data

    @property
    def info_slave_data(self):
        if self._info_slave_data is None:
            info_slave_data = ('IFLA_INFO_SLAVE_DATA', {'attrs': []})
            self._info_slave_data = info_slave_data[1]['attrs']
            self.linkinfo.append(info_slave_data)
        return self._info_slave_data

    def get_vf(self, spec):
        vflist = []
        if not isinstance(spec, (list, tuple)):
            spec = (spec,)
        for vf in spec:
            vfcfg = []
            # pop VF index
            vfid = vf.pop('vf')  # mandatory
            # pop VLAN spec
            vlan = vf.pop('vlan', None)  # optional
            if isinstance(vlan, int):
                vfcfg.append(('IFLA_VF_VLAN', {'vf': vfid, 'vlan': vlan}))
            elif isinstance(vlan, dict):
                vlan['vf'] = vfid
                vfcfg.append(('IFLA_VF_VLAN', vlan))
            elif isinstance(vlan, (list, tuple)):
                vlist = []
                for vspec in vlan:
                    vspec['vf'] = vfid
                    vlist.append(('IFLA_VF_VLAN_INFO', vspec))
                vfcfg.append(('IFLA_VF_VLAN_LIST', {'attrs': vlist}))
            # pop rate spec
            rate = vf.pop('rate', None)  # optional
            if rate is not None:
                rate['vf'] = vfid
                vfcfg.append(('IFLA_VF_RATE', rate))
            # create simple VF attrs
            for attr in vf:
                vfcfg.append(
                    (
                        ifinfmsg.vflist.vfinfo.name2nla(attr),
                        {'vf': vfid, attr: vf[attr]},
                    )
                )
            vflist.append(('IFLA_VF_INFO', {'attrs': vfcfg}))
        return {'attrs': vflist}
