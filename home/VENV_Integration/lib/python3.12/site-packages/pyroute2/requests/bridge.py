from pyroute2.netlink.rtnl.ifinfmsg import ifinfmsg, protinfo_bridge

from .common import Index, IPRouteFilter, NLAKeyTransform


class BridgeFieldFilter(Index, NLAKeyTransform):
    _nla_prefix = ifinfmsg.prefix


class BridgeIPRouteFilter(IPRouteFilter):
    def build_vlan_info_spec(self, orig_spec):
        range_vids = [int(i) for i in str(orig_spec['vid']).split('-')]
        if len(range_vids) == 2:
            if 0 < int(range_vids[0]) < range_vids[1] < 4095:
                new_spec = []
                new_spec.append(
                    {
                        'vid': range_vids[0],
                        'flags': self.convert_flags('range_begin'),
                    }
                )
                new_spec.append(
                    {
                        'vid': range_vids[1],
                        'flags': self.convert_flags('range_end'),
                    }
                )
                return new_spec
        elif len(range_vids) == 1:
            if 0 < range_vids[0] < 4095:
                # PVID?
                if 'pvid' in orig_spec.keys():
                    if orig_spec['pvid']:
                        orig_spec['flags'] = self.convert_flags(
                            ['pvid', 'untagged']
                        )
                        del orig_spec['pvid']
                # Make sure the vid is an int.
                orig_spec['vid'] = range_vids[0]
                return [orig_spec]
        return []

    def build_vlan_tunnel_info_spec(self, orig_spec):
        # vlan_tunnel_info uses the same format as vlan_info,
        # just adds tunnel_id.
        vlan_info_spec = self.build_vlan_info_spec(orig_spec)
        range_ids = [int(i) for i in str(orig_spec['id']).split('-')]
        if len(range_ids) == 2 and len(vlan_info_spec) == 2:
            if 0 < range_ids[0] < range_ids[1] < 16777215:
                # vid to id mapping range must be the same length
                if (
                    vlan_info_spec[1]['vid'] - vlan_info_spec[0]['vid']
                    == range_ids[1] - range_ids[0]
                ):
                    vlan_info_spec[0]['id'] = range_ids[0]
                    vlan_info_spec[1]['id'] = range_ids[1]
                    return [
                        self.create_nla_spec(vlan_info_spec[0]),
                        self.create_nla_spec(vlan_info_spec[1]),
                    ]
        elif len(range_ids) == 1 and len(vlan_info_spec) == 1:
            if 0 < range_ids[0] < 4095:
                vlan_info_spec[0]['id'] = range_ids[0]
                # Delete flags because vlan_tunnel_info doesn't seem
                #  to use them, except for the RANGE.
                try:
                    del vlan_info_spec[0]['flags']
                except KeyError:
                    pass
                return [self.create_nla_spec(vlan_info_spec[0])]
        return []

    def create_nla_spec(self, spec):
        attrs = []
        for key in spec.keys():
            nla = ifinfmsg.af_spec_bridge.vlan_tunnel_info.name2nla(key)
            attrs.append([nla, spec[key]])
        return {'attrs': attrs}

    def convert_flags(self, flags):
        if isinstance(flags, int):
            return flags
        elif isinstance(flags, str):
            return ifinfmsg.af_spec_bridge.vlan_info.names2flags([flags])
        elif isinstance(flags, list):
            return ifinfmsg.af_spec_bridge.vlan_info.names2flags(flags)
        return 0

    def build_spec(self, orig_spec):
        if 'vid' in orig_spec.keys():
            if 'id' in orig_spec.keys():
                return self.build_vlan_tunnel_info_spec(orig_spec)
            else:
                return self.build_vlan_info_spec(orig_spec)
        return []

    def finalize(self, context):
        if self.command != 'dump':
            if 'IFLA_AF_SPEC' not in context:
                context['IFLA_AF_SPEC'] = {'attrs': []}
            for key in ('vlan_info', 'vlan_tunnel_info'):
                if key in context:
                    nla = ifinfmsg.af_spec_bridge.name2nla(key)
                    new_spec = self.build_spec(context[key])
                    for spec in new_spec:
                        context['IFLA_AF_SPEC']['attrs'].append([nla, spec])
                    try:
                        del context[key]
                    except KeyError:
                        pass
            for key in ('mode', 'vlan_flags'):
                if key in context:
                    nla = ifinfmsg.af_spec_bridge.name2nla(key)
                    context['IFLA_AF_SPEC']['attrs'].append(
                        [nla, context[key]]
                    )
                    try:
                        del context[key]
                    except KeyError:
                        pass


class BridgePortFieldFilter(IPRouteFilter):
    _nla_prefix = ifinfmsg.prefix
    _allowed = [x[0] for x in protinfo_bridge.nla_map]
    _allowed.append('attrs')

    def finalize(self, context):
        keys = tuple(context.keys())
        context['attrs'] = []
        for key in keys:
            context['attrs'].append(
                (protinfo_bridge.name2nla(key), context[key])
            )
