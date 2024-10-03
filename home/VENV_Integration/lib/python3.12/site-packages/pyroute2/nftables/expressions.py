import socket
import struct
from collections import OrderedDict


##
# Utility functions
##
def get_mask(addr):
    if not addr:
        return [None, None]
    ret = addr.split('/')
    if len(ret) == 2:
        return ret
    else:
        return [addr, None]


##
# Expressions generators
##
def genex(name, kwarg):
    exp_data = []
    for key, value in kwarg.items():
        exp_data.append(('NFTA_%s_%s' % (name.upper(), key.upper()), value))
    return {
        'attrs': [
            ('NFTA_EXPR_NAME', name),
            ('NFTA_EXPR_DATA', {'attrs': exp_data}),
        ]
    }


def verdict(code):
    kwarg = OrderedDict()
    kwarg['dreg'] = 0  # NFT_REG_VERDICT
    kwarg['data'] = {
        'attrs': [
            ('NFTA_DATA_VERDICT', {'attrs': [('NFTA_VERDICT_CODE', code)]})
        ]
    }
    return [genex('immediate', kwarg)]


def ipv4addr(src=None, dst=None):
    if not src and not dst:
        raise ValueError('must be at least one of src, dst')

    ret = []
    # get masks
    src, src_mask = get_mask(src)
    dst, dst_mask = get_mask(dst)

    # load address(es) into NFT_REG_1
    kwarg = OrderedDict()
    kwarg['dreg'] = 1  # save to NFT_REG_1
    kwarg['base'] = 1  # NFT_PAYLOAD_NETWORK_HEADER
    kwarg['offset'] = 12 if src else 16
    kwarg['len'] = 8 if (src and dst) else 4
    ret.append(genex('payload', kwarg))

    # run bitwise with masks -- if provided
    if src_mask or dst_mask:
        mask = b''
        if src:
            if not src_mask:
                src_mask = '32'
            src_mask = int('1' * int(src_mask), 2)
            mask += struct.pack('I', src_mask)
        if dst:
            if not dst_mask:
                dst_mask = '32'
            dst_mask = int('1' * int(dst_mask), 2)
            mask += struct.pack('I', dst_mask)
        xor = '\x00' * len(mask)
        kwarg = OrderedDict()
        kwarg['sreg'] = 1  # read from NFT_REG_1
        kwarg['dreg'] = 1  # save to NFT_REG_1
        kwarg['len'] = 8 if (src and dst) else 4
        kwarg['mask'] = {'attrs': [('NFTA_DATA_VALUE', mask)]}
        kwarg['xor'] = {'attrs': [('NFTA_DATA_VALUE', xor)]}
        ret.append(genex('bitwise', kwarg))

    # run cmp
    packed = b''
    if src:
        packed += socket.inet_aton(src)
    if dst:
        packed += socket.inet_aton(dst)
    kwarg = OrderedDict()
    kwarg['sreg'] = 1  # read from NFT_REG_1
    kwarg['op'] = 0  # NFT_CMP_EQ
    kwarg['data'] = {'attrs': [('NFTA_DATA_VALUE', packed)]}
    ret.append(genex('cmp', kwarg))
    return ret
