from struct import pack, unpack

from pyroute2.netlink import nla

TCF_EM_OPND_EQ = 0
TCF_EM_OPND_GT = 1
TCF_EM_OPND_LT = 2

OPERANDS_DICT = {
    TCF_EM_OPND_EQ: ('eq', '='),
    TCF_EM_OPND_GT: ('gt', '>'),
    TCF_EM_OPND_LT: ('lt', '<'),
}

# meta types
TCF_META_TYPE_VAR = 0
TCF_META_TYPE_INT = 1

TCF_META_ID_MASK = 0x7FF
TCF_META_TYPE_MASK = 0xF << 12

# see tc_em_meta.h
META_ID = {
    'value': 0,
    'random': 1,
    'loadavg_0': 2,
    'loadavg_1': 3,
    'loadavg_2': 4,
    'dev': 5,
    'priority': 6,
    'protocol': 7,
    'pkttype': 8,
    'pktlen': 9,
    'datalen': 10,
    'maclen': 11,
    'nfmark': 12,
    'tcindex': 13,
    'rtclassid': 14,
    'rtiif': 15,
    'sk_family': 16,
    'sk_state': 17,
    'sk_reuse': 18,
    'sk_bound_if': 19,
    'sk_refcnt': 20,
    'sk_shutdown': 21,
    'sk_proto': 22,
    'sk_type': 23,
    'sk_rcvbuf': 24,
    'sk_rmem_alloc': 25,
    'sk_wmem_alloc': 26,
    'sk_omem_alloc': 27,
    'sk_wmem_queued': 28,
    'sk_rcv_qlen': 29,
    'sk_snd_qlen': 30,
    'sk_err_qlen': 31,
    'sk_forward_allocs': 32,
    'sk_sndbuf': 33,
    'sk_allocs': 34,
    'sk_route_caps': 35,
    'sk_hash': 36,
    'sk_lingertime': 37,
    'sk_ack_backlog': 38,
    'sk_max_ack_backlog': 39,
    'sk_prio': 40,
    'sk_rcvlowat': 41,
    'sk_rcvtimeo': 42,
    'sk_sndtimeo': 43,
    'sk_sendmsg_off': 44,
    'sk_write_pending': 45,
    'vlan_tag': 46,
    'rxhash': 47,
}

strings_meta = ('dev', 'sk_bound_if')


class data(nla):
    nla_map = (
        ('TCA_EM_META_UNSPEC', 'none'),
        ('TCA_EM_META_HDR', 'tca_em_meta_header_parse'),
        ('TCA_EM_META_LVALUE', 'uint32'),
        ('TCA_EM_META_RVALUE', 'hex'),
    )

    def decode(self):
        self.header = None
        self.length = 24
        nla.decode(self)

        # Patch to have a better view in nldecap
        attrs = dict(self['attrs'])
        rvalue = attrs.get('TCA_EM_META_RVALUE')
        meta_hdr = attrs.get('TCA_EM_META_HDR')
        meta_id = meta_hdr['id']
        rvalue = bytearray.fromhex(rvalue.replace(':', ''))
        if meta_id == 'TCF_META_TYPE_VAR':
            rvalue.decode('utf-8')
        if meta_id == 'TCF_META_TYPE_INT':
            rvalue = unpack('<I', rvalue)[0]
        self['attrs'][2] = ('TCA_EM_META_RVALUE', rvalue)

    def encode(self):
        if 'object' not in self:
            raise ValueError('An object definition must be given!')

        if 'value' not in self:
            raise ValueError('A value must be given!')

        # The value can either be a string or an int depending
        # on the selected meta kind.
        # It is really important to distinct them otherwise
        # the kernel won't be nice with us...
        value = self['value']
        kind = self['object'].get('kind')
        if not kind:
            raise ValueError('Not meta kind specified!')
        else:
            if kind in strings_meta:
                if not isinstance(value, str):
                    raise ValueError(
                        '{} kinds have to use string value!'.format(
                            ' and '.join(strings_meta)
                        )
                    )
                else:
                    value = value.encode('utf-8')
            else:
                if not isinstance(value, int):
                    raise ValueError(
                        'Invalid value specified, it must ' 'be an integer'
                    )
                else:
                    value = pack('<I', value)

        self['attrs'].append(['TCA_EM_META_HDR', self['object']])
        self['attrs'].append(['TCA_EM_META_LVALUE', self.get('mask', 0)])
        self['attrs'].append(['TCA_EM_META_RVALUE', value])
        nla.encode(self)

        # Patch NLA structure
        self['header']['length'] -= 4
        self.data = self.data[4:]

    class tca_em_meta_header_parse(nla):
        fields = (
            ('kind', 'H'),
            ('shift', 'B'),
            ('opnd', 'B'),
            ('id', 'H'),
            ('pad', 'H'),
        )

        def decode(self):
            nla.decode(self)

            self['id'] = (self['kind'] & TCF_META_TYPE_MASK) >> 12
            if self['id'] == TCF_META_TYPE_VAR:
                self['id'] = 'TCF_META_TYPE_VAR'
            elif self['id'] == TCF_META_TYPE_INT:
                self['id'] = 'TCF_META_TYPE_INT'
            else:
                pass

            self['kind'] &= TCF_META_ID_MASK
            for k, v in META_ID.items():
                if self['kind'] == v:
                    self['kind'] = 'TCF_META_ID_{}'.format(k.upper())

            fmt = 'TCF_EM_OPND_{}'.format(
                OPERANDS_DICT[self['opnd']][0].upper()
            )
            self['opnd'] = fmt
            del self['pad']

        def encode(self):
            if not isinstance(self['kind'], str):
                raise ValueError("kind' keywords must be set!")

            kind = self['kind'].lower()
            if kind in strings_meta:
                self['id'] = TCF_META_TYPE_VAR
            else:
                self['id'] = TCF_META_TYPE_INT
            self['id'] <<= 12

            for k, v in META_ID.items():
                if kind == k:
                    self['kind'] = self['id'] | v
                    break

            if isinstance(self['opnd'], str):
                for k, v in OPERANDS_DICT.items():
                    if self['opnd'].lower() in v:
                        self['opnd'] = k
                        break

            # Perform sanity checks on 'shift' value
            if isinstance(self['shift'], str):
                # If it fails, it will raise a ValueError
                # which is what we want
                self['shift'] = int(self['shift'])
            if not 0 <= self['shift'] <= 255:
                raise ValueError(
                    "'shift' value must be between" "0 and 255 included!"
                )
            nla.encode(self)
