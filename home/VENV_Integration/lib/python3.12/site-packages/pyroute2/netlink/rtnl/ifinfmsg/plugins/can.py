from pyroute2.netlink import nla, nlmsg_atoms

CAN_CTRLMODE_NAMES = {
    'CAN_CTRLMODE_LOOPBACK': 0x01,
    'CAN_CTRLMODE_LISTENONLY': 0x02,
    'CAN_CTRLMODE_3_SAMPLES': 0x04,
    'CAN_CTRLMODE_ONE_SHOT': 0x08,
    'CAN_CTRLMODE_BERR_REPORTING': 0x10,
    'CAN_CTRLMODE_FD': 0x20,
    'CAN_CTRLMODE_PRESUME_ACK': 0x40,
    'CAN_CTRLMODE_FD_NON_ISO': 0x80,
    'CAN_CTRLMODE_CC_LEN8_DLC': 0x100,
    'CAN_CTRLMODE_TDC_AUTO': 0x200,
    'CAN_CTRLMODE_TDC_MANUAL': 0x400,
}

CAN_CTRLMODE_VALUES = {
    0x001: 'CAN_CTRLMODE_LOOPBACK',
    0x002: 'CAN_CTRLMODE_LISTENONLY',
    0x004: 'CAN_CTRLMODE_3_SAMPLES',
    0x008: 'CAN_CTRLMODE_ONE_SHOT',
    0x010: 'CAN_CTRLMODE_BERR_REPORTING',
    0x020: 'CAN_CTRLMODE_FD',
    0x040: 'CAN_CTRLMODE_PRESUME_ACK',
    0x080: 'CAN_CTRLMODE_FD_NON_ISO',
    0x100: 'CAN_CTRLMODE_CC_LEN8_DLC',
    0x200: 'CAN_CTRLMODE_TDC_AUTO',
    0x400: 'CAN_CTRLMODE_TDC_MANUAL',
}


class can(nla):
    prefix = 'IFLA_'
    nla_map = (
        ('IFLA_CAN_UNSPEC', 'none'),
        ('IFLA_CAN_BITTIMING', 'can_bittiming'),
        ('IFLA_CAN_BITTIMING_CONST', 'can_bittiming_const'),
        # NOTE:
        # This is actually a struct of one member, but that doesn't parse:
        ('IFLA_CAN_CLOCK', 'uint32'),
        ('IFLA_CAN_STATE', 'can_state'),
        ('IFLA_CAN_CTRLMODE', 'can_ctrlmode'),
        ('IFLA_CAN_RESTART_MS', 'uint32'),
        ('IFLA_CAN_RESTART', 'flag'),
        ('IFLA_CAN_BERR_COUNTER', 'can_berr_counter'),
        ('IFLA_CAN_DATA_BITTIMING', 'can_bittiming'),
        ('IFLA_CAN_DATA_BITTIMING_CONST', 'can_bittiming_const'),
        ('IFLA_CAN_TERMINATION', 'uint16'),
        ('IFLA_CAN_TERMINATION_CONST', 'array(uint16)'),
        ('IFLA_CAN_BITRATE_CONST', 'array(uint32)'),
        ('IFLA_CAN_DATA_BITRATE_CONST', 'array(uint32)'),
        ('IFLA_CAN_BITRATE_MAX', 'uint32'),
        ('IFLA_CAN_TDC', 'can_tdc'),
        ('IFLA_CAN_CTRLMODE_EXT', 'can_ctrlmode_ext'),
    )

    class can_bittiming(nla):
        fields = (
            ('bitrate', 'I'),
            ('sample_point', 'I'),
            ('tq', 'I'),
            ('prop_seg', 'I'),
            ('phase_seg1', 'I'),
            ('phase_seg2', 'I'),
            ('sjw', 'I'),
            ('brp', 'I'),
        )

    class can_bittiming_const(nla):
        fields = (
            ('name', '=16s'),
            ('tseg1_min', 'I'),
            ('tseg1_max', 'I'),
            ('tseg2_min', 'I'),
            ('tseg2_max', 'I'),
            ('sjw_max', 'I'),
            ('brp_min', 'I'),
            ('brp_max', 'I'),
            ('brp_inc', 'I'),
        )

    class can_state(nlmsg_atoms.uint32):
        value_map = {
            0: 'ERROR_ACTIVE',
            1: 'ERROR_WARNING',
            2: 'ERROR_PASSIVE',
            3: 'BUS_OFF',
            4: 'STOPPED',
            5: 'SLEEPING',
            6: 'MAX',
        }

    class can_ctrlmode(nla):
        fields = (('mask', 'I'), ('flags', 'I'))

        def decode(self):
            super(nla, self).decode()
            flags = self["flags"]
            for value, mode in CAN_CTRLMODE_VALUES.items():
                self[mode[len('CAN_CTRLMODE_') :].lower()] = (
                    "on" if flags & value else "off"
                )
            del self["flags"]
            del self["mask"]

        def encode(self):
            mask = 0
            flags = 0
            for mode, value in CAN_CTRLMODE_NAMES.items():
                m = mode[len('CAN_CTRLMODE_') :].lower()
                try:
                    v = self[m]
                except KeyError:
                    continue
                mask |= value
                if v == "on":
                    flags |= value
            self['mask'] = mask
            self['flags'] = flags
            return super(nla, self).encode()

    class can_berr_counter(nla):
        fields = (('txerr', 'H'), ('rxerr', 'H'))

    class can_tdc(nla):
        prefix = "IFLA_"
        nla_map = (
            ('IFLA_CAN_TDC_UNSPEC', 'none'),
            ('IFLA_CAN_TDC_TDCV_MIN', 'uint32'),
            ('IFLA_CAN_TDC_TDCV_MAX', 'uint32'),
            ('IFLA_CAN_TDC_TDCO_MIN', 'uint32'),
            ('IFLA_CAN_TDC_TDCO_MAX', 'uint32'),
            ('IFLA_CAN_TDC_TDCF_MIN', 'uint32'),
            ('IFLA_CAN_TDC_TDCF_MAX', 'uint32'),
            ('IFLA_CAN_TDC_TDCV', 'uint32'),
            ('IFLA_CAN_TDC_TDCO', 'uint32'),
            ('IFLA_CAN_TDC_TDCF', 'uint32'),
        )

    class can_ctrlmode_ext(nla):
        prefix = "IFLA_"
        nla_map = (
            ('IFLA_CAN_CTRLMODE_UNSPEC', 'none'),
            ('IFLA_CAN_CTRLMODE_SUPPORTED', 'can_ctrlmode_supported'),
        )

        class can_ctrlmode_supported(nlmsg_atoms.uint32):
            def decode(self):
                super(nlmsg_atoms.uint32, self).decode()
                for value, mode in CAN_CTRLMODE_VALUES.items():
                    self[mode[len('CAN_CTRLMODE_') :].lower()] = (
                        'yes' if value & self["value"] else 'no'
                    )
                del self["value"]
