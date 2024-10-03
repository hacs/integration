"""
nf_tables expression netlink attributes

See EXPRESSIONS in nft(8).
"""

from socket import AF_INET, AF_INET6

from pyroute2.nftables.parser.parser import conv_map_tuple, nfta_nla_parser


class NFTReg(object):
    def __init__(self, num):
        self.num = num

    @classmethod
    def from_netlink(cls, nlval):
        # please, for more information read nf_tables.h.
        if nlval == 'NFT_REG_VERDICT':
            num = 0
        else:
            num = int(nlval.split('_')[-1].lower())
            if nlval.startswith('NFT_REG32_'):
                num += 8
        return cls(num=num)

    @staticmethod
    def to_netlink(reg):
        # please, for more information read nf_tables.h.
        if reg.num == 0:
            return 'NFT_REG_VERDICT'
        if reg.num < 8:
            return 'NFT_REG_{0}'.format(reg.num)
        return 'NFT_REG32_{0}'.format(reg.num)

    @classmethod
    def from_dict(cls, val):
        return cls(num=val)

    def to_dict(self):
        return self.num


class NFTVerdict(object):
    def __init__(self, verdict, chain):
        self.verdict = verdict
        self.chain = chain

    @classmethod
    def from_netlink(cls, ndmsg):
        if ndmsg.get_attr('NFTA_VERDICT_CODE') is not None:
            verdict = (
                ndmsg.get_attr('NFTA_VERDICT_CODE').split('_')[-1].lower()
            )
        else:
            verdict = None
        chain = ndmsg.get_attr('NFTA_VERDICT_CHAIN')
        return cls(verdict=verdict, chain=chain)

    def to_netlink(self):
        attrs = [('NFTA_VERDICT_CODE', 'NF_' + self.verdict)]
        if self.chain is not None:
            attrs.append(('NFTA_VERDICT_CHAIN', self.chain))
        return attrs

    @classmethod
    def from_dict(cls, d):
        return cls(verdict=d['verdict'], chain=d.get('chain', None))

    def to_dict(self):
        d = {'verdict': self.verdict}
        if self.chain is not None:
            d['chain'] = self.chain
        return d


class NFTData(object):
    def __init__(self, data_type, data):
        self.type = data_type
        self.data = data

    def to_netlink(self):
        if self.type == 'value':
            return ('NFTA_DATA_VALUE', self.data)
        if self.type == 'verdict':
            return ('NFTA_DATA_VERDICT', self.data)
        raise NotImplementedError(self.type)

    @classmethod
    def from_netlink(cls, ndmsg):
        if ndmsg.get_attr('NFTA_DATA_VALUE') is not None:
            kwargs = {
                'data_type': 'value',
                'data': ndmsg.get_attr('NFTA_DATA_VALUE'),
            }
        elif ndmsg.get_attr('NFTA_DATA_VERDICT') is not None:
            kwargs = {
                'data_type': 'verdict',
                'data': NFTVerdict.from_netlink(
                    ndmsg.get_attr('NFTA_DATA_VERDICT')
                ),
            }
        else:
            raise NotImplementedError(ndmsg)
        return cls(**kwargs)

    @classmethod
    def from_dict(cls, data):
        def from_32hex(val):
            return bytes(bytearray.fromhex(val[2:]))[::-1]

        kwargs = {}
        data = data["reg"]
        if data['type'] == 'value':
            value = bytes()
            for i in range(0, data['len'], 4):
                value += from_32hex(data['data{0}'.format(i / 4)])
            kwargs['data'] = value
        elif data['type'] == 'verdict':
            kwargs['data'] = NFTVerdict.from_dict(data)
        else:
            raise NotImplementedError()
        kwargs['data_type'] = data['type']
        return cls(**kwargs)

    def to_dict(self):
        def to_32hex(s):
            res = ''.join('{:02x}'.format(c) for c in bytearray(s)[::-1])
            return '0x' + res.zfill(8)

        if self.type == 'value':
            len_data = len(self.data)
            d = {'type': 'value', 'len': len_data}
            for i in range(0, len_data, 4):
                d['data{0}'.format(i / 4)] = to_32hex(self.data[i : i + 4])
        elif self.type == 'verdict':
            d = self.data.to_dict()
            d['type'] = 'verdict'
        else:
            raise NotImplementedError()
        return {"reg": d}


class NFTRuleExpr(nfta_nla_parser):
    #######################################################################
    conv_maps = (conv_map_tuple('name', 'NFTA_EXPR_NAME', 'type', 'raw'),)
    #######################################################################

    @classmethod
    def from_netlink(cls, expr_type, ndmsg):
        inst = super(NFTRuleExpr, cls).from_netlink(ndmsg)
        inst.name = expr_type
        return inst

    cparser_reg = NFTReg
    cparser_data = NFTData

    class cparser_extract_str(object):
        STRVAL = None

        @classmethod
        def from_netlink(cls, val):
            magic = '{0}'
            left, right = cls.STRVAL.split(magic, 1)
            if right:
                val = val[len(left) : -len(right)]
            else:
                val = val[len(left) :]
            return val.lower()

        @classmethod
        def to_netlink(cls, val):
            return cls.STRVAL.format(val).upper()

        @staticmethod
        def from_dict(val):
            return val

        @staticmethod
        def to_dict(val):
            return val

    class cparser_inet_family(object):
        @staticmethod
        def from_netlink(val):
            if val == AF_INET:
                return 'ip'
            if val == AF_INET6:
                return 'ip6'
            return val

        @staticmethod
        def to_netlink(val):
            if val == 'ip':
                return AF_INET
            if val == 'ip6':
                return AF_INET6
            return val

        @staticmethod
        def from_dict(val):
            return val

        @staticmethod
        def to_dict(val):
            return val


class ExprMeta(NFTRuleExpr):
    conv_maps = NFTRuleExpr.conv_maps + (
        conv_map_tuple('key', 'NFTA_META_KEY', 'key', 'meta_key'),
        conv_map_tuple('dreg', 'NFTA_META_DREG', 'dreg', 'reg'),
    )

    class cparser_meta_key(NFTRuleExpr.cparser_extract_str):
        STRVAL = 'NFT_META_{0}'


class ExprCmp(NFTRuleExpr):
    conv_maps = NFTRuleExpr.conv_maps + (
        conv_map_tuple('sreg', 'NFTA_CMP_SREG', 'sreg', 'reg'),
        conv_map_tuple('op', 'NFTA_CMP_OP', 'op', 'cmp_op'),
        conv_map_tuple('data', 'NFTA_CMP_DATA', 'data', 'data'),
    )

    class cparser_cmp_op(NFTRuleExpr.cparser_extract_str):
        STRVAL = 'NFT_CMP_{0}'


class ExprImmediate(NFTRuleExpr):
    conv_maps = NFTRuleExpr.conv_maps + (
        conv_map_tuple('dreg', 'NFTA_IMMEDIATE_DREG', 'dreg', 'reg'),
        conv_map_tuple('data', 'NFTA_IMMEDIATE_DATA', 'data', 'data'),
    )


class ExprPayload(NFTRuleExpr):
    conv_maps = NFTRuleExpr.conv_maps + (
        conv_map_tuple('dreg', 'NFTA_PAYLOAD_DREG', 'dreg', 'reg'),
        conv_map_tuple('base', 'NFTA_PAYLOAD_BASE', 'base', 'payload_base'),
        conv_map_tuple('offset', 'NFTA_PAYLOAD_OFFSET', 'offset', 'raw'),
        conv_map_tuple('len', 'NFTA_PAYLOAD_LEN', 'len', 'raw'),
    )

    class cparser_payload_base(NFTRuleExpr.cparser_extract_str):
        STRVAL = 'NFT_PAYLOAD_{0}_HEADER'

        @classmethod
        def from_netlink(cls, ndmsg):
            val = super(ExprPayload.cparser_payload_base, cls).from_netlink(
                ndmsg
            )
            if val == 'll':
                return 'link'
            return val

        @classmethod
        def to_netlink(cls, val):
            if val == 'link':
                val = 'll'
            return super(ExprPayload.cparser_payload_base, cls).to_netlink(val)

        @staticmethod
        def from_dict(val):
            return val

        @staticmethod
        def to_dict(val):
            return val


class ExprLookup(NFTRuleExpr):
    conv_maps = NFTRuleExpr.conv_maps + (
        conv_map_tuple('setid', 'NFTA_LOOKUP_SET', 'set', 'raw'),
        conv_map_tuple('sreg', 'NFTA_LOOKUP_SREG', 'sreg', 'reg'),
        conv_map_tuple('flags', 'NFTA_LOOKUP_FLAGS', 'flags', 'raw'),
    )


class ExprNat(NFTRuleExpr):
    conv_maps = NFTRuleExpr.conv_maps + (
        conv_map_tuple('nat_type', 'NFTA_NAT_TYPE', 'nat_type', 'nat_type'),
        conv_map_tuple('family', 'NFTA_NAT_FAMILY', 'family', 'inet_family'),
        conv_map_tuple(
            'sreg_addr_min', 'NFTA_NAT_REG_ADDR_MIN', 'sreg_addr_min', 'reg'
        ),
        conv_map_tuple(
            'sreg_addr_max', 'NFTA_NAT_REG_ADDR_MAX', 'sreg_addr_max', 'reg'
        ),
    )

    class cparser_nat_type(NFTRuleExpr.cparser_extract_str):
        STRVAL = 'NFT_NAT_{0}'


class ExprBitwise(NFTRuleExpr):
    conv_maps = NFTRuleExpr.conv_maps + (
        conv_map_tuple('sreg', 'NFTA_BITWISE_SREG', 'sreg', 'reg'),
        conv_map_tuple('dreg', 'NFTA_BITWISE_DREG', 'dreg', 'reg'),
        conv_map_tuple('len', 'NFTA_BITWISE_LEN', 'len', 'raw'),
        conv_map_tuple('mask', 'NFTA_BITWISE_MASK', 'mask', 'data'),
        conv_map_tuple('xor', 'NFTA_BITWISE_XOR', 'xor', 'data'),
    )


class ExprCounter(NFTRuleExpr):
    conv_maps = NFTRuleExpr.conv_maps + (
        conv_map_tuple('bytes', 'NFTA_COUNTER_BYTES', 'bytes', 'raw'),
        conv_map_tuple('packets', 'NFTA_COUNTER_PACKETS', 'pkts', 'raw'),
    )


class ExprMatch(NFTRuleExpr):
    conv_maps = NFTRuleExpr.conv_maps + (
        conv_map_tuple('match_name', 'NFTA_MATCH_NAME', 'name', 'raw'),
    )


class ExprTarget(NFTRuleExpr):
    conv_maps = NFTRuleExpr.conv_maps + (
        conv_map_tuple('target_name', 'NFTA_TARGET_NAME', 'name', 'raw'),
    )


NFTA_EXPR_NAME_MAP = {
    'meta': ExprMeta,
    'cmp': ExprCmp,
    'immediate': ExprImmediate,
    'payload': ExprPayload,
    'lookup': ExprLookup,
    'nat': ExprNat,
    'bitwise': ExprBitwise,
    'counter': ExprCounter,
    'match': ExprMatch,
    'target': ExprTarget,
}


def get_expression_from_netlink(ndmsg):
    name = ndmsg.get_attr('NFTA_EXPR_NAME')
    try:
        expr_cls = NFTA_EXPR_NAME_MAP[name]
    except KeyError:
        raise NotImplementedError(
            "can't load rule expression {0} from netlink {1}".format(
                name, ndmsg
            )
        )
    return expr_cls.from_netlink(name, ndmsg.get_attr('NFTA_EXPR_DATA'))


def get_expression_from_dict(d):
    name = d['type']
    if name in NFTA_EXPR_NAME_MAP:
        expr_cls = NFTA_EXPR_NAME_MAP[name]
    else:
        raise NotImplementedError(
            "can't load rule expression {0} from json {1}".format(name, d)
        )
    return expr_cls.from_dict(d)
