from socket import AF_INET6

from pyroute2.common import AF_MPLS
from pyroute2.netlink.rtnl import encap_type, rt_proto, rt_scope, rt_type
from pyroute2.netlink.rtnl.rtmsg import IP6_RT_PRIO_USER, LWTUNNEL_ENCAP_MPLS
from pyroute2.netlink.rtnl.rtmsg import nh as nh_header
from pyroute2.netlink.rtnl.rtmsg import rtmsg

from .common import IPRouteFilter, IPTargets, MPLSTarget, NLAKeyTransform

encap_types = {'mpls': 1, AF_MPLS: 1, 'seg6': 5, 'bpf': 6, 'seg6local': 7}


class RouteFieldFilter(IPTargets, NLAKeyTransform):
    _nla_prefix = 'RTA_'

    def __init__(self, add_defaults=True):
        self.add_defaults = add_defaults

    def index(self, key, context, value):
        if isinstance(value, (list, tuple)):
            value = value[0]
        return {key: value}

    def set_oif(self, context, value):
        return self.index('oif', context, value)

    def set_iif(self, context, value):
        return self.index('iif', context, value)

    def set_family(self, context, value):
        if value == AF_MPLS:
            return {'family': AF_MPLS, 'dst_len': 20, 'table': 254, 'type': 1}
        return {'family': value}

    def set_priority(self, context, value):
        '''
        In the kernel:

        .. code-block:: c

            static int inet6_rtm_newroute(...)
            {
                ...
                if (cfg.fc_metric == 0)
                    cfg.fc_metric = IP6_RT_PRIO_USER;
                ...
            }
        '''
        if context.get('family') == AF_INET6 and value == 0:
            return {'priority': IP6_RT_PRIO_USER}
        return {'priority': value}

    def set_flags(self, context, value):
        if context.get('family') == AF_MPLS:
            return {}
        if isinstance(value, (list, tuple, str)):
            return {'flags': rtmsg.names2flags(value)}
        return {'flags': value}

    def set_encap(self, context, value):
        # FIXME: planned for the next refactoring cycle
        if isinstance(value, dict) and value.get('type') == 'mpls':
            na = []
            target = None
            labels = value.get('labels', [])
            if isinstance(labels, (dict, int)):
                labels = [labels]
            if isinstance(labels, str):
                labels = labels.split('/')
            for label in labels:
                target = MPLSTarget(label)
                target['bos'] = 0
                na.append(target)
            target['bos'] = 1
            return {'encap_type': LWTUNNEL_ENCAP_MPLS, 'encap': na}
        return {'encap': value}

    def set_scope(self, context, value):
        if isinstance(value, str):
            return {'scope': rt_scope[value]}
        return {'scope': value}

    def set_proto(self, context, value):
        if isinstance(value, str):
            return {'proto': rt_proto[value]}
        return {'proto': value}

    def set_encap_type(self, context, value):
        if isinstance(value, str):
            return {'encap_type': encap_type[value]}
        return {'encap_type': value}

    def set_type(self, context, value):
        if isinstance(value, str):
            return {'type': rt_type[value]}
        return {'type': value}


class RouteIPRouteFilter(IPRouteFilter):
    def set_metrics(self, context, value):
        if value and 'attrs' not in value:
            metrics = {'attrs': []}
            for name, metric in value.items():
                rtax = rtmsg.metrics.name2nla(name)
                if metric is not None:
                    metrics['attrs'].append([rtax, metric])
            if metrics['attrs']:
                return {'metrics': metrics}
        return {}

    def set_multipath(self, context, value):
        if value:
            ret = []
            for v in value:
                if 'attrs' in v:
                    ret.append(v)
                    continue
                nh = {'attrs': []}
                nh_fields = [x[0] for x in nh_header.fields]
                for name in nh_fields:
                    nh[name] = v.get(name, 0)
                for name in v:
                    if name in nh_fields or v[name] is None:
                        continue
                    if name == 'encap' and isinstance(v[name], dict):
                        if (
                            v[name].get('type', None) is None
                            or v[name].get('labels', None) is None
                        ):
                            continue
                        nh['attrs'].append(
                            [
                                'RTA_ENCAP_TYPE',
                                encap_types.get(
                                    v[name]['type'], v[name]['type']
                                ),
                            ]
                        )
                        nh['attrs'].append(
                            ['RTA_ENCAP', self.encap_header(v[name])]
                        )
                    elif name == 'newdst':
                        nh['attrs'].append(
                            ['RTA_NEWDST', self.mpls_rta(v[name])]
                        )
                    else:
                        rta = rtmsg.name2nla(name)
                        nh['attrs'].append([rta, v[name]])
                ret.append(nh)
            if ret:
                return {'multipath': ret}
        return {}

    def set_encap(self, context, value):
        if (
            isinstance(value, (list, tuple))
            and context.get('encap_type') == LWTUNNEL_ENCAP_MPLS
        ):
            return {'encap': {'attrs': [['MPLS_IPTUNNEL_DST', value]]}}
        elif isinstance(value, dict):
            # human-friendly form:
            #
            # 'encap': {'type': 'mpls',
            #           'labels': '200/300'}
            #
            # 'type' is mandatory
            if 'type' in value and 'labels' in value:
                return {
                    'encap_type': encap_types.get(
                        value['type'], value['type']
                    ),
                    'encap': self.encap_header(value),
                }
            # human-friendly form:
            #
            # 'encap': {'type': 'seg6',
            #           'mode': 'encap'
            #           'segs': '2000::5,2000::6'}
            #
            # 'encap': {'type': 'seg6',
            #           'mode': 'inline'
            #           'segs': '2000::5,2000::6'
            #           'hmac': 1}
            #
            # 'encap': {'type': 'seg6',
            #           'mode': 'encap'
            #           'segs': '2000::5,2000::6'
            #           'hmac': 0xf}
            #
            # 'encap': {'type': 'seg6',
            #           'mode': 'inline'
            #           'segs': ['2000::5', '2000::6']}
            #
            # 'type', 'mode' and 'segs' are mandatory
            if 'type' in value and 'mode' in value and 'segs' in value:
                return {
                    'encap_type': encap_types.get(
                        value['type'], value['type']
                    ),
                    'encap': self.encap_header(value),
                }
            elif 'type' in value and (
                'in' in value or 'out' in value or 'xmit' in value
            ):
                return {
                    'encap_type': encap_types.get(
                        value['type'], value['type']
                    ),
                    'encap': self.encap_header(value),
                }
            # human-friendly form:
            #
            # 'encap': {'type': 'seg6local',
            #           'action': 'End'}
            #
            # 'encap': {'type': 'seg6local',
            #           'action': 'End.DT6',
            #           'table': '10'}
            #
            # 'encap': {'type': 'seg6local',
            #           'action': 'End.DT4',
            #           'vrf_table': 10}
            #
            # 'encap': {'type': 'seg6local',
            #           'action': 'End.DT46',
            #           'vrf_table': 10}
            #
            # 'encap': {'type': 'seg6local',
            #           'action': 'End.DX6',
            #           'nh6': '2000::5'}
            #
            # 'encap': {'type': 'seg6local',
            #           'action': 'End.B6'
            #           'srh': {'segs': '2000::5,2000::6',
            #                   'hmac': 0xf}}
            #
            # 'type' and 'action' are mandatory
            elif 'type' in value and 'action' in value:
                return {
                    'encap_type': encap_types.get(
                        value['type'], value['type']
                    ),
                    'encap': self.encap_header(value),
                }
        return {}

    def finalize(self, context):
        for key in context:
            if context[key] in ('', None):
                try:
                    del context[key]
                except KeyError:
                    pass

    def mpls_rta(self, value):
        # FIXME: planned for the next refactoring cycle
        ret = []
        if not isinstance(value, (list, tuple, set)):
            value = (value,)
        for label in value:
            ret.append(MPLSTarget(label))
        if ret:
            ret[-1]['bos'] = 1
        return ret

    def encap_header(self, header):
        '''
        Encap header transform. Format samples:

            {'type': 'mpls',
             'labels': '200/300'}

            {'type': AF_MPLS,
             'labels': (200, 300)}

            {'type': 'mpls',
             'labels': 200}

            {'type': AF_MPLS,
             'labels': [{'bos': 0, 'label': 200, 'ttl': 16},
                        {'bos': 1, 'label': 300, 'ttl': 16}]}
        '''
        if isinstance(header['type'], int) or (
            header['type'] in ('mpls', AF_MPLS, LWTUNNEL_ENCAP_MPLS)
        ):
            ret = []
            override_bos = True
            labels = header['labels']
            if isinstance(labels, str):
                labels = labels.split('/')
            if not isinstance(labels, (tuple, list, set)):
                labels = (labels,)
            for label in labels:
                if isinstance(label, dict):
                    # dicts append intact
                    override_bos = False
                    ret.append(label)
                else:
                    # otherwise construct label dict
                    if isinstance(label, str):
                        label = int(label)
                    ret.append({'bos': 0, 'label': label})
            # the last label becomes bottom-of-stack
            if override_bos:
                ret[-1]['bos'] = 1
            return {'attrs': [['MPLS_IPTUNNEL_DST', ret]]}
        '''
        Seg6 encap header transform. Format samples:

            {'type': 'seg6',
             'mode': 'encap',
             'segs': '2000::5,2000::6'}

            {'type': 'seg6',
             'mode': 'encap'
             'segs': '2000::5,2000::6',
             'hmac': 1}
        '''
        if header['type'] == 'seg6':
            # Init step
            ret = {}
            # Parse segs
            segs = header['segs']
            # If they are in the form in_addr6,in_addr6
            if isinstance(segs, str):
                # Create an array with the splitted values
                temp = segs.split(',')
                # Init segs
                segs = []
                # Iterate over the values
                for seg in temp:
                    # Discard empty string
                    if seg != '':
                        # Add seg to segs
                        segs.append(seg)
            # Retrieve mode
            mode = header['mode']
            # hmac is optional and contains the hmac key
            hmac = header.get('hmac', None)
            # Construct the new object
            ret = {'mode': mode, 'segs': segs}
            # If hmac is present convert to u32
            if hmac:
                # Add to ret the hmac key
                ret['hmac'] = hmac & 0xFFFFFFFF
            # Done return the object
            return {'attrs': [['SEG6_IPTUNNEL_SRH', ret]]}
        '''
        BPF encap header transform. Format samples:

            {'type': 'bpf',
             'in': {'fd':4, 'name':'firewall'}}

            {'type': 'bpf',
             'in'  : {'fd':4, 'name':'firewall'},
             'out' : {'fd':5, 'name':'stats'},
             'xmit': {'fd':6, 'name':'vlan_push', 'headroom':4}}
        '''
        if header['type'] == 'bpf':
            attrs = {}
            for key, value in header.items():
                if key not in ['in', 'out', 'xmit']:
                    continue

                obj = [
                    ['LWT_BPF_PROG_FD', value['fd']],
                    ['LWT_BPF_PROG_NAME', value['name']],
                ]
                if key == 'in':
                    attrs['LWT_BPF_IN'] = {'attrs': obj}
                elif key == 'out':
                    attrs['LWT_BPF_OUT'] = {'attrs': obj}
                elif key == 'xmit':
                    attrs['LWT_BPF_XMIT'] = {'attrs': obj}
                    if 'headroom' in value:
                        attrs['LWT_BPF_XMIT_HEADROOM'] = value['headroom']

            return {'attrs': list(attrs.items())}
        '''
        Seg6 encap header transform. Format samples:

            {'type': 'seg6local',
             'action': 'End.DT6',
             'table': '10'}

            {'type': 'seg6local',
             'action': 'End.DT4',
             'vrf_table': 10}

            {'type': 'seg6local',
             'action': 'End.DT46',
             'vrf_table': 10}

            {'type': 'seg6local',
             'action': 'End.B6',
             'table': '10'
             'srh': {'segs': '2000::5,2000::6'}}
        '''
        if header['type'] == 'seg6local':
            # Init step
            ret = {}
            table = None
            nh4 = None
            nh6 = None
            iif = None  # Actually not used
            oif = None
            srh = {}
            segs = []
            hmac = None
            prog_fd = None
            prog_name = None
            vrf_table = None
            # Parse segs
            if srh:
                segs = header['srh']['segs']
                # If they are in the form in_addr6,in_addr6
                if isinstance(segs, str):
                    # Create an array with the splitted values
                    temp = segs.split(',')
                    # Init segs
                    segs = []
                    # Iterate over the values
                    for seg in temp:
                        # Discard empty string
                        if seg != '':
                            # Add seg to segs
                            segs.append(seg)
                # hmac is optional and contains the hmac key
                hmac = header.get('hmac', None)
            # Retrieve action
            action = header['action']
            if action == 'End.X':
                # Retrieve nh6
                nh6 = header['nh6']
            elif action == 'End.T':
                # Retrieve table and convert to u32
                table = header['table'] & 0xFFFFFFFF
            elif action == 'End.DX2':
                # Retrieve oif and convert to u32
                oif = header['oif'] & 0xFFFFFFFF
            elif action == 'End.DX6':
                # Retrieve nh6
                nh6 = header['nh6']
            elif action == 'End.DX4':
                # Retrieve nh6
                nh4 = header['nh4']
            elif action == 'End.DT6':
                # Retrieve table
                table = header['table']
            elif action == 'End.DT4':
                # Retrieve vrf_table
                vrf_table = header['vrf_table']
            elif action == 'End.DT46':
                # Retrieve vrf_table
                vrf_table = header['vrf_table']
            elif action == 'End.B6':
                # Parse segs
                segs = header['srh']['segs']
                # If they are in the form in_addr6,in_addr6
                if isinstance(segs, str):
                    # Create an array with the splitted values
                    temp = segs.split(',')
                    # Init segs
                    segs = []
                    # Iterate over the values
                    for seg in temp:
                        # Discard empty string
                        if seg != '':
                            # Add seg to segs
                            segs.append(seg)
                # hmac is optional and contains the hmac key
                hmac = header.get('hmac', None)
                srh['segs'] = segs
                # If hmac is present convert to u32
                if hmac:
                    # Add to ret the hmac key
                    srh['hmac'] = hmac & 0xFFFFFFFF
                srh['mode'] = 'inline'
            elif action == 'End.B6.Encaps':
                # Parse segs
                segs = header['srh']['segs']
                # If they are in the form in_addr6,in_addr6
                if isinstance(segs, str):
                    # Create an array with the splitted values
                    temp = segs.split(',')
                    # Init segs
                    segs = []
                    # Iterate over the values
                    for seg in temp:
                        # Discard empty string
                        if seg != '':
                            # Add seg to segs
                            segs.append(seg)
                # hmac is optional and contains the hmac key
                hmac = header.get('hmac', None)
                srh['segs'] = segs
                if hmac:
                    # Add to ret the hmac key
                    srh['hmac'] = hmac & 0xFFFFFFFF
                srh['mode'] = 'encap'
            elif action == 'End.BPF':
                prog_fd = header['bpf']['fd']
                prog_name = header['bpf']['name']

            # Construct the new object
            ret = []
            ret.append(['SEG6_LOCAL_ACTION', {'value': action}])
            if table:
                # Add the table to ret
                ret.append(['SEG6_LOCAL_TABLE', {'value': table}])
            if vrf_table:
                # Add the vrf_table to ret
                ret.append(['SEG6_LOCAL_VRFTABLE', {'value': vrf_table}])
            if nh4:
                # Add the nh4 to ret
                ret.append(['SEG6_LOCAL_NH4', {'value': nh4}])
            if nh6:
                # Add the nh6 to ret
                ret.append(['SEG6_LOCAL_NH6', {'value': nh6}])
            if iif:
                # Add the iif to ret
                ret.append(['SEG6_LOCAL_IIF', {'value': iif}])
            if oif:
                # Add the oif to ret
                ret.append(['SEG6_LOCAL_OIF', {'value': oif}])
            if srh:
                # Add the srh to ret
                ret.append(['SEG6_LOCAL_SRH', srh])
            if prog_fd and prog_name:
                # Add the prog_fd and prog_name to ret
                ret.append(
                    [
                        'SEG6_LOCAL_BPF',
                        {
                            'attrs': [
                                ['LWT_BPF_PROG_FD', prog_fd],
                                ['LWT_BPF_PROG_NAME', prog_name],
                            ]
                        },
                    ]
                )
            # Done return the object
            return {'attrs': ret}
