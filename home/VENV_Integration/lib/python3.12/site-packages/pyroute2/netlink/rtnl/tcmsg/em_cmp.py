from pyroute2.netlink import nla

TCF_EM_OPND_EQ = 0
TCF_EM_OPND_GT = 1
TCF_EM_OPND_LT = 2

OPERANDS_DICT = {
    TCF_EM_OPND_EQ: ('eq', '='),
    TCF_EM_OPND_GT: ('gt', '>'),
    TCF_EM_OPND_LT: ('lt', '<'),
}

# align types
TCF_EM_ALIGN_U8 = 1
TCF_EM_ALIGN_U16 = 2
TCF_EM_ALIGN_U32 = 4

ALIGNS_DICT = {
    TCF_EM_ALIGN_U8: 'u8',
    TCF_EM_ALIGN_U16: 'u16',
    TCF_EM_ALIGN_U32: 'u32',
}

# layer types
TCF_LAYER_LINK = 0
TCF_LAYER_NETWORK = 1
TCF_LAYER_TRANSPORT = 2

LAYERS_DICT = {
    TCF_LAYER_LINK: ('link', 'eth'),
    TCF_LAYER_NETWORK: ('network', 'ip'),
    TCF_LAYER_TRANSPORT: ('transport', 'tcp'),
}

# see tc_em_cmp.h
TCF_EM_CMP_TRANS = 1


class data(nla):
    fields = (
        ('val', 'I'),
        ('mask', 'I'),
        ('off', 'H'),
        ('align_flags', 'B'),
        ('layer_opnd', 'B'),
    )

    def decode(self):
        self.header = None
        self.length = 24
        nla.decode(self)
        self['align'] = self['align_flags'] & 0x0F
        self['flags'] = (self['align_flags'] & 0xF0) >> 4
        self['layer'] = self['layer_opnd'] & 0x0F
        self['opnd'] = (self['layer_opnd'] & 0xF0) >> 4
        del self['layer_opnd']
        del self['align_flags']

        # Perform translation for readability with nldecap
        self['layer'] = 'TCF_LAYER_{}'.format(
            LAYERS_DICT[self['layer']][0]
        ).upper()
        self['align'] = 'TCF_EM_ALIGN_{}'.format(
            ALIGNS_DICT[self['align']]
        ).upper()
        self['opnd'] = 'TCF_EM_OPND_{}'.format(
            OPERANDS_DICT[self['opnd']][0]
        ).upper()

    def encode(self):
        # Set default values
        self['layer_opnd'] = 0
        self['align_flags'] = 0

        # Build align_flags byte
        if 'trans' in self:
            self['align_flags'] = TCF_EM_CMP_TRANS << 4
        for k, v in ALIGNS_DICT.items():
            if self['align'].lower() == v:
                self['align_flags'] |= k
                break

        # Build layer_opnd byte
        if isinstance(self['opnd'], int):
            self['layer_opnd'] = self['opnd'] << 4
        else:
            for k, v in OPERANDS_DICT.items():
                if self['opnd'].lower() in v:
                    self['layer_opnd'] = k << 4
                    break

        # Layer code
        if isinstance(self['layer'], int):
            self['layer_opnd'] |= self['layer']
        else:
            for k, v in LAYERS_DICT.items():
                if self['layer'].lower() in v:
                    self['layer_opnd'] |= k
                    break

        self['off'] = self.get('offset', 0)
        self['val'] = self.get('value', 0)
        nla.encode(self)

        # Patch NLA structure
        self['header']['length'] -= 4
        self.data = self.data[4:]
