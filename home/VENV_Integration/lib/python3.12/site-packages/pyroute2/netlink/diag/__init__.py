from socket import AF_INET, AF_INET6, AF_UNIX, IPPROTO_TCP, inet_ntop
from struct import pack

from pyroute2.netlink import (
    NETLINK_SOCK_DIAG,
    NLM_F_MATCH,
    NLM_F_REQUEST,
    NLM_F_ROOT,
    nla,
    nlmsg,
)
from pyroute2.netlink.nlsocket import Marshal, NetlinkSocket

SOCK_DIAG_BY_FAMILY = 20
SOCK_DESTROY = 21

# states
SS_UNKNOWN = 0
SS_ESTABLISHED = 1
SS_SYN_SENT = 2
SS_SYN_RECV = 3
SS_FIN_WAIT1 = 4
SS_FIN_WAIT2 = 5
SS_TIME_WAIT = 6
SS_CLOSE = 7
SS_CLOSE_WAIT = 8
SS_LAST_ACK = 9
SS_LISTEN = 10
SS_CLOSING = 11
SS_MAX = 12

SS_ALL = (1 << SS_MAX) - 1
SS_CONN = SS_ALL & ~(
    (1 << SS_LISTEN)
    | (1 << SS_CLOSE)
    | (1 << SS_TIME_WAIT)
    | (1 << SS_SYN_RECV)
)

# multicast groups ids (for use with {add,drop}_membership)
SKNLGRP_NONE = 0
SKNLGRP_INET_TCP_DESTROY = 1
SKNLGRP_INET_UDP_DESTROY = 2
SKNLGRP_INET6_TCP_DESTROY = 3
SKNLGRP_INET6_UDP_DESTROY = 4


class sock_diag_req(nlmsg):
    fields = (('sdiag_family', 'B'), ('sdiag_protocol', 'B'))


UDIAG_SHOW_NAME = 0x01
UDIAG_SHOW_VFS = 0x02
UDIAG_SHOW_PEER = 0x04
UDIAG_SHOW_ICONS = 0x08
UDIAG_SHOW_RQLEN = 0x10
UDIAG_SHOW_MEMINFO = 0x20


class inet_addr_codec(nlmsg):
    def encode(self):
        # FIXME: add human-friendly API to specify IP addresses as str
        # (see also decode())
        if self['idiag_src'] == 0:
            self['idiag_src'] = (0, 0, 0, 0)
        if self['idiag_dst'] == 0:
            self['idiag_dst'] = (0, 0, 0, 0)
        nlmsg.encode(self)

    def decode(self):
        nlmsg.decode(self)
        if self[self.ffname] == AF_INET:
            self['idiag_dst'] = inet_ntop(
                AF_INET, pack('>I', self['idiag_dst'][0])
            )
            self['idiag_src'] = inet_ntop(
                AF_INET, pack('>I', self['idiag_src'][0])
            )
        elif self[self.ffname] == AF_INET6:
            self['idiag_dst'] = inet_ntop(
                AF_INET6, pack('>IIII', *self['idiag_dst'])
            )
            self['idiag_src'] = inet_ntop(
                AF_INET6, pack('>IIII', *self['idiag_src'])
            )


class inet_diag_req(inet_addr_codec):
    ffname = 'sdiag_family'
    fields = (
        ('sdiag_family', 'B'),
        ('sdiag_protocol', 'B'),
        ('idiag_ext', 'B'),
        ('__pad', 'B'),
        ('idiag_states', 'I'),
        ('idiag_sport', '>H'),
        ('idiag_dport', '>H'),
        ('idiag_src', '>4I'),
        ('idiag_dst', '>4I'),
        ('idiag_if', 'I'),
        ('idiag_cookie', 'Q'),
    )


class inet_diag_msg(inet_addr_codec):
    ffname = 'idiag_family'
    fields = (
        ('idiag_family', 'B'),
        ('idiag_state', 'B'),
        ('idiag_timer', 'B'),
        ('idiag_retrans', 'B'),
        ('idiag_sport', '>H'),
        ('idiag_dport', '>H'),
        ('idiag_src', '>4I'),
        ('idiag_dst', '>4I'),
        ('idiag_if', 'I'),
        ('idiag_cookie', 'Q'),
        ('idiag_expires', 'I'),
        ('idiag_rqueue', 'I'),
        ('idiag_wqueue', 'I'),
        ('idiag_uid', 'I'),
        ('idiag_inode', 'I'),
    )

    nla_map = (
        ('INET_DIAG_NONE', 'none'),
        ('INET_DIAG_MEMINFO', 'inet_diag_meminfo'),
        # FIXME: must be protocol specific?
        ('INET_DIAG_INFO', 'tcp_info'),
        ('INET_DIAG_VEGASINFO', 'tcpvegas_info'),
        ('INET_DIAG_CONG', 'asciiz'),
        ('INET_DIAG_TOS', 'hex'),
        ('INET_DIAG_TCLASS', 'hex'),
        ('INET_DIAG_SKMEMINFO', 'hex'),
        ('INET_DIAG_SHUTDOWN', 'uint8'),
        ('INET_DIAG_DCTCPINFO', 'tcp_dctcp_info'),
        ('INET_DIAG_PROTOCOL', 'hex'),
        ('INET_DIAG_SKV6ONLY', 'uint8'),
        ('INET_DIAG_LOCALS', 'hex'),
        ('INET_DIAG_PEERS', 'hex'),
        ('INET_DIAG_PAD', 'hex'),
        ('INET_DIAG_MARK', 'hex'),
        ('INET_DIAG_BBRINFO', 'tcp_bbr_info'),
        ('INET_DIAG_CLASS_ID', 'uint32'),
        ('INET_DIAG_MD5SIG', 'hex'),
        ('INET_DIAG_ULP_INFO', 'hex'),
        ('INET_DIAG_SK_BPF_STORAGES', 'hex'),
        ('INET_DIAG_CGROUP_ID', 'uint64'),
    )

    class inet_diag_meminfo(nla):
        fields = (
            ('idiag_rmem', 'I'),
            ('idiag_wmem', 'I'),
            ('idiag_fmem', 'I'),
            ('idiag_tmem', 'I'),
        )

    class tcpvegas_info(nla):
        fields = (
            ('tcpv_enabled', 'I'),
            ('tcpv_rttcnt', 'I'),
            ('tcpv_rtt', 'I'),
            ('tcpv_minrtt', 'I'),
        )

    class tcp_dctcp_info(nla):
        fields = (
            ('dctcp_enabled', 'H'),
            ('dctcp_ce_state', 'H'),
            ('dctcp_alpha', 'I'),
            ('dctcp_ab_ecn', 'I'),
            ('dctcp_ab_tot', 'I'),
        )

    class tcp_bbr_info(nla):
        fields = (
            ('bbr_bw_lo', 'I'),
            ('bbr_bw_hi', 'I'),
            ('bbr_min_rtt', 'I'),
            ('bbr_pacing_gain', 'I'),
            ('bbr_cwnd_gain', 'I'),
        )

    class tcp_info(nla):
        fields = (
            ('tcpi_state', 'B'),
            ('tcpi_ca_state', 'B'),
            ('tcpi_retransmits', 'B'),
            ('tcpi_probes', 'B'),
            ('tcpi_backoff', 'B'),
            ('tcpi_options', 'B'),
            ('tcpi_snd_wscale', 'B'),  # tcpi_rcv_wscale -- in decode()
            ('tcpi_delivery_rate_app_limited', 'B'),
            ('tcpi_rto', 'I'),
            ('tcpi_ato', 'I'),
            ('tcpi_snd_mss', 'I'),
            ('tcpi_rcv_mss', 'I'),
            ('tcpi_unacked', 'I'),
            ('tcpi_sacked', 'I'),
            ('tcpi_lost', 'I'),
            ('tcpi_retrans', 'I'),
            ('tcpi_fackets', 'I'),
            # Times
            ('tcpi_last_data_sent', 'I'),
            ('tcpi_last_ack_sent', 'I'),
            ('tcpi_last_data_recv', 'I'),
            ('tcpi_last_ack_recv', 'I'),
            # Metrics
            ('tcpi_pmtu', 'I'),
            ('tcpi_rcv_ssthresh', 'I'),
            ('tcpi_rtt', 'I'),
            ('tcpi_rttvar', 'I'),
            ('tcpi_snd_ssthresh', 'I'),
            ('tcpi_snd_cwnd', 'I'),
            ('tcpi_advmss', 'I'),
            ('tcpi_reordering', 'I'),
            ('tcpi_rcv_rtt', 'I'),
            ('tcpi_rcv_space', 'I'),
            ('tcpi_total_retrans', 'I'),
            ('tcpi_pacing_rate', 'Q'),
            ('tcpi_max_pacing_rate', 'Q'),
            ('tcpi_bytes_acked', 'Q'),
            ('tcpi_bytes_received', 'Q'),
            ('tcpi_segs_out', 'I'),
            ('tcpi_segs_in', 'I'),
            ('tcpi_notsent_bytes', 'I'),
            ('tcpi_min_rtt', 'I'),
            ('tcpi_data_segs_in', 'I'),
            ('tcpi_data_segs_out', 'I'),
            ('tcpi_delivery_rate', 'Q'),
            ('tcpi_busy_time', 'Q'),
            ('tcpi_rwnd_limited', 'Q'),
            ('tcpi_sndbuf_limited', 'Q'),
            ('tcpi_delivered', 'I'),
            ('tcpi_delivered_ce', 'I'),
            ('tcpi_bytes_sent', 'Q'),
            ('tcpi_bytes_retrans', 'Q'),
            ('tcpi_dsack_dups', 'I'),
            ('tcpi_reord_seen', 'I'),
            ('tcpi_rcv_ooopack', 'I'),
            ('tcpi_snd_wnd', 'I'),
        )

        def decode(self):
            # Fix tcpi_rcv_scale amd delivery_rate bit fields.
            # In the C:
            #
            # __u8    tcpi_snd_wscale : 4, tcpi_rcv_wscale : 4;
            # __u8    tcpi_delivery_rate_app_limited:1;
            #
            nla.decode(self)
            self['tcpi_rcv_wscale'] = self['tcpi_snd_wscale'] & 0xF
            self['tcpi_snd_wscale'] = self['tcpi_snd_wscale'] & 0xF0 >> 4
            self['tcpi_delivery_rate_app_limited'] = (
                self['tcpi_delivery_rate_app_limited'] & 0x80 >> 7
            )


class unix_diag_req(nlmsg):
    fields = (
        ('sdiag_family', 'B'),
        ('sdiag_protocol', 'B'),
        ('__pad', 'H'),
        ('udiag_states', 'I'),
        ('udiag_ino', 'I'),
        ('udiag_show', 'I'),
        ('udiag_cookie', 'Q'),
    )


class unix_diag_msg(nlmsg):
    fields = (
        ('udiag_family', 'B'),
        ('udiag_type', 'B'),
        ('udiag_state', 'B'),
        ('__pad', 'B'),
        ('udiag_ino', 'I'),
        ('udiag_cookie', 'Q'),
    )

    nla_map = (
        ('UNIX_DIAG_NAME', 'asciiz'),
        ('UNIX_DIAG_VFS', 'unix_diag_vfs'),
        ('UNIX_DIAG_PEER', 'uint32'),
        ('UNIX_DIAG_ICONS', 'hex'),
        ('UNIX_DIAG_RQLEN', 'unix_diag_rqlen'),
        ('UNIX_DIAG_MEMINFO', 'hex'),
        ('UNIX_DIAG_SHUTDOWN', 'uint8'),
    )

    class unix_diag_vfs(nla):
        fields = (('udiag_vfs_ino', 'I'), ('udiag_vfs_dev', 'I'))

    class unix_diag_rqlen(nla):
        fields = (('udiag_rqueue', 'I'), ('udiag_wqueue', 'I'))


class MarshalDiag(Marshal):
    key_format = 'B'
    # The family goes after the nlmsg header,
    # IHHII = 4 + 2 + 2 + 4 + 4 = 16 bytes
    key_offset = 16
    # Please notice that the SOCK_DIAG Marshal
    # uses not the nlmsg type, but sdiag_family
    # to choose the proper class
    msg_map = {
        AF_UNIX: unix_diag_msg,
        AF_INET: inet_diag_msg,
        AF_INET6: inet_diag_msg,
    }
    # error type NLMSG_ERROR == 2 == AF_INET,
    # it doesn't work for DiagSocket that way,
    # so disable the error messages for now
    error_type = -1


class DiagSocket(NetlinkSocket):
    '''
    Usage::

        from pyroute2 import DiagSocket
        with DiagSocket() as ds:
            ds.bind()
            sstats = ds.get_sock_stats()

    '''

    def __init__(self, fileno=None):
        super(DiagSocket, self).__init__(NETLINK_SOCK_DIAG)
        self.marshal = MarshalDiag()

    def get_sock_stats(
        self,
        family=AF_UNIX,
        states=SS_ALL,
        protocol=IPPROTO_TCP,
        extensions=0,
        show=(
            UDIAG_SHOW_NAME
            | UDIAG_SHOW_VFS
            | UDIAG_SHOW_PEER
            | UDIAG_SHOW_ICONS
        ),
    ):
        '''
        Get sockets statistics.

        ACHTUNG: the get_sock_stats() signature will be changed
        before the next release, this one is a WIP-code!
        '''

        if family == AF_UNIX:
            req = unix_diag_req()
            req['udiag_states'] = states
            req['udiag_show'] = show
        elif family in (AF_INET, AF_INET6):
            req = inet_diag_req()
            req['idiag_states'] = states
            req['sdiag_protocol'] = protocol
            req['idiag_ext'] = extensions
        else:
            raise NotImplementedError()
        req['sdiag_family'] = family

        return tuple(
            self.nlm_request(
                req,
                SOCK_DIAG_BY_FAMILY,
                NLM_F_REQUEST | NLM_F_ROOT | NLM_F_MATCH,
            )
        )
