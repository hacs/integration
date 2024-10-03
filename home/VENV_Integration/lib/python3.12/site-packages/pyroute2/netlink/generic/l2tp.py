from pyroute2.netlink import (
    NLA_F_NESTED,
    NLM_F_ACK,
    NLM_F_DUMP,
    NLM_F_REQUEST,
    genlmsg,
    nla,
)
from pyroute2.netlink.generic import GenericNetlinkSocket

# Defines from uapi/linux/l2tp.h
L2TP_GENL_NAME = "l2tp"
L2TP_GENL_VERSION = 1

L2TP_CMD_NOOP = 0
L2TP_CMD_TUNNEL_CREATE = 1
L2TP_CMD_TUNNEL_DELETE = 2
L2TP_CMD_TUNNEL_MODIFY = 3
L2TP_CMD_TUNNEL_GET = 4
L2TP_CMD_SESSION_CREATE = 5
L2TP_CMD_SESSION_DELETE = 6
L2TP_CMD_SESSION_MODIFY = 7
L2TP_CMD_SESSION_GET = 8

# ATTR types defined for L2TP
L2TP_ATTR_NONE = 0
L2TP_ATTR_PW_TYPE = 1
L2TP_ATTR_ENCAP_TYPE = 2
L2TP_ATTR_OFFSET = 3
L2TP_ATTR_DATA_SEQ = 4
L2TP_ATTR_L2SPEC_TYPE = 5
L2TP_ATTR_L2SPEC_LEN = 6
L2TP_ATTR_PROTO_VERSION = 7
L2TP_ATTR_IFNAME = 8
L2TP_ATTR_CONN_ID = 9
L2TP_ATTR_PEER_CONN_ID = 10
L2TP_ATTR_SESSION_ID = 11
L2TP_ATTR_PEER_SESSION_ID = 12
L2TP_ATTR_UDP_CSUM = 13
L2TP_ATTR_VLAN_ID = 14
L2TP_ATTR_COOKIE = 15
L2TP_ATTR_PEER_COOKIE = 16
L2TP_ATTR_DEBUG = 17
L2TP_ATTR_RECV_SEQ = 18
L2TP_ATTR_SEND_SEQ = 19
L2TP_ATTR_LNS_MODE = 20
L2TP_ATTR_USING_IPSEC = 21
L2TP_ATTR_RECV_TIMEOUT = 22
L2TP_ATTR_FD = 23
L2TP_ATTR_IP_SADDR = 24
L2TP_ATTR_IP_DADDR = 25
L2TP_ATTR_UDP_SPORT = 26
L2TP_ATTR_UDP_DPORT = 27
L2TP_ATTR_MTU = 28
L2TP_ATTR_MRU = 29
L2TP_ATTR_STATS = 30
L2TP_ATTR_IP6_SADDR = 31
L2TP_ATTR_IP6_DADDR = 32
L2TP_ATTR_UDP_ZERO_CSUM6_TX = 33
L2TP_ATTR_UDP_ZERO_CSUM6_RX = 34
L2TP_ATTR_PAD = 35

# Nested L2TP_ATTR_STATS
L2TP_ATTR_STATS_NONE = 0
L2TP_ATTR_TX_PACKETS = 1
L2TP_ATTR_TX_BYTES = 2
L2TP_ATTR_TX_ERRORS = 3
L2TP_ATTR_RX_PACKETS = 4
L2TP_ATTR_RX_BYTES = 5
L2TP_ATTR_RX_SEQ_DISCARDS = 6
L2TP_ATTR_RX_OOS_PACKETS = 7
L2TP_ATTR_RX_ERRORS = 8
L2TP_ATTR_STATS_PAD = 9

L2TP_PWTYPE_NONE = 0x0000
L2TP_PWTYPE_ETH_VLAN = 0x0004
L2TP_PWTYPE_ETH = 0x0005
L2TP_PWTYPE_PPP = 0x0007
L2TP_PWTYPE_PPP_AC = 0x0008
L2TP_PWTYPE_IP = 0x000B

L2TP_L2SPECTYPE_NONE = 0
L2TP_L2SPECTYPE_DEFAULT = 1

L2TP_ENCAPTYPE_UDP = 0
L2TP_ENCAPTYPE_IP = 1


class l2tpmsg(genlmsg):
    prefix = "L2TP_ATTR_"

    nla_map = (
        ("L2TP_ATTR_NONE", "none"),
        ("L2TP_ATTR_PW_TYPE", "uint16"),
        ("L2TP_ATTR_ENCAP_TYPE", "uint16"),
        ("L2TP_ATTR_OFFSET", "uint16"),
        ("L2TP_ATTR_DATA_SEQ", "uint8"),
        ("L2TP_ATTR_L2SPEC_TYPE", "uint8"),
        ("L2TP_ATTR_L2SPEC_LEN", "uint8"),
        ("L2TP_ATTR_PROTO_VERSION", "uint8"),
        ("L2TP_ATTR_IFNAME", "asciiz"),
        ("L2TP_ATTR_CONN_ID", "uint32"),
        ("L2TP_ATTR_PEER_CONN_ID", "uint32"),
        ("L2TP_ATTR_SESSION_ID", "uint32"),
        ("L2TP_ATTR_PEER_SESSION_ID", "uint32"),
        ("L2TP_ATTR_UDP_CSUM", "uint8"),
        ("L2TP_ATTR_VLAN_ID", "uint16"),
        ("L2TP_ATTR_COOKIE", "hex"),
        ("L2TP_ATTR_PEER_COOKIE", "hex"),
        ("L2TP_ATTR_DEBUG", "uint32"),
        ("L2TP_ATTR_RECV_SEQ", "uint8"),
        ("L2TP_ATTR_SEND_SEQ", "uint8"),
        ("L2TP_ATTR_LNS_MODE", "uint8"),
        ("L2TP_ATTR_USING_IPSEC", "uint8"),
        ("L2TP_ATTR_RECV_TIMEOUT", "uint64"),
        ("L2TP_ATTR_FD", "uint32"),
        ("L2TP_ATTR_IP_SADDR", "ip4addr"),
        ("L2TP_ATTR_IP_DADDR", "ip4addr"),
        ("L2TP_ATTR_UDP_SPORT", "uint16"),
        ("L2TP_ATTR_UDP_DPORT", "uint16"),
        ("L2TP_ATTR_MTU", "uint16"),
        ("L2TP_ATTR_MRU", "uint16"),
        ("L2TP_ATTR_STATS", "l2tp_stats"),
        ("L2TP_ATTR_IP6_SADDR", "ip6addr"),
        ("L2TP_ATTR_IP6_DADDR", "ip6addr"),
        ("L2TP_ATTR_UDP_ZERO_CSUM6_TX", "flag"),
        ("L2TP_ATTR_UDP_ZERO_CSUM6_RX", "flag"),
        ("L2TP_ATTR_PAD", "none"),
    )

    class l2tp_stats(nla):
        nla_flags = NLA_F_NESTED
        nla_map = (
            ("L2TP_ATTR_STATS_NONE", "none"),
            ("L2TP_ATTR_TX_PACKETS", "uint64"),
            ("L2TP_ATTR_TX_BYTES", "uint64"),
            ("L2TP_ATTR_TX_ERRORS", "uint64"),
            ("L2TP_ATTR_RX_PACKETS", "uint64"),
            ("L2TP_ATTR_RX_BYTES", "uint64"),
            ("L2TP_ATTR_RX_SEQ_DISCARDS", "uint64"),
            ("L2TP_ATTR_RX_OOS_PACKETS", "uint64"),
            ("L2TP_ATTR_RX_ERRORS", "uint64"),
            ("L2TP_ATTR_STATS_PAD", "none"),
        )


class L2tp(GenericNetlinkSocket):
    def __init__(self, *args, **kwargs):
        GenericNetlinkSocket.__init__(self, *args, **kwargs)
        self.bind(L2TP_GENL_NAME, l2tpmsg)

    def _do_request(self, msg, msg_flags=NLM_F_REQUEST | NLM_F_ACK):
        return self.nlm_request(msg, msg_type=self.prid, msg_flags=msg_flags)

    def _send_tunnel(
        self,
        cmd,
        tunnel_id,
        peer_tunnel_id=None,
        protocol=3,
        remote=None,
        local=None,
        fd=None,
        encap="udp",
        udp_sport=None,
        udp_dport=None,
        udp_csum=None,
        udp6_csum_rx=None,
        udp6_csum_tx=None,
        debug=None,
    ):
        """
        Send L2TP tunnel create or modify commands
        :param cmd: Netlink command to use
        :param tunnel_id: local tunnel id
        :param peer_tunnel_id: remote tunnel id
        :param protocol: L2TP version
        :param remote: IP address of the remote peer
        :param local: IP address of the local interface
        :param fd: file descriptor of socket to use
        :param encap: encapsulation type of the tunnel (udp, ip)
        :param udp_sport: UDP source port to be used for the tunnel
        :param udp_dport: UDP destination port to be used for the tunnel
        :param udp_csum: control if IPv4 UDP checksums should be calculated and
                         checked
        :param udp6_csum_rx: control if IPv6 UDP rx checksums should be
                             calculated
        :param udp6_csum_tx: control if IPv6 UDP tx checksums should be
                             calculated
        :param debug: enable or disable debugging using kernel printk for the
                      tunnel
        :return: Netlink response
        """
        msg = l2tpmsg()
        msg["cmd"] = cmd
        msg["version"] = L2TP_GENL_VERSION
        msg["attrs"].append(["L2TP_ATTR_CONN_ID", tunnel_id])

        if cmd == L2TP_CMD_TUNNEL_CREATE:
            msg["attrs"].append(["L2TP_ATTR_PEER_CONN_ID", peer_tunnel_id])
            msg["attrs"].append(["L2TP_ATTR_PROTO_VERSION", protocol])

        if encap == "ip":
            msg["attrs"].append(["L2TP_ATTR_ENCAP_TYPE", L2TP_ENCAPTYPE_IP])
        elif encap == "udp":
            msg["attrs"].append(["L2TP_ATTR_ENCAP_TYPE", L2TP_ENCAPTYPE_UDP])

        if fd:
            msg["attrs"].append(["L2TP_ATTR_FD", fd])
        else:
            local_ip_version = 4
            if local:
                if local.find(":") > -1:
                    local_ip_version = 6

                if local_ip_version == 6:
                    msg["attrs"].append(["L2TP_ATTR_IP6_SADDR", local])
                else:
                    msg["attrs"].append(["L2TP_ATTR_IP_SADDR", local])

            remote_ip_version = 4
            if remote:
                if remote.find(":") > -1:
                    remote_ip_version = 6

                if remote_ip_version == 6:
                    msg["attrs"].append(["L2TP_ATTR_IP6_DADDR", remote])
                else:
                    msg["attrs"].append(["L2TP_ATTR_IP_DADDR", remote])

            if local and remote:
                if remote_ip_version != local_ip_version:
                    raise ValueError(
                        "Local and remote peer address version mismatch"
                    )

            if encap == "udp" and cmd == L2TP_CMD_TUNNEL_CREATE:
                if udp_sport:
                    msg["attrs"].append(["L2TP_ATTR_UDP_SPORT", udp_sport])
                if udp_dport:
                    msg["attrs"].append(["L2TP_ATTR_UDP_DPORT", udp_dport])
                if udp_csum:
                    msg["attrs"].append(["L2TP_ATTR_UDP_CSUM", True])
                if udp6_csum_rx:
                    msg["attrs"].append(["L2TP_ATTR_UDP_ZERO_CSUM6_TX", True])
                if udp6_csum_tx:
                    msg["attrs"].append(["L2TP_ATTR_UDP_ZERO_CSUM6_RX", True])

        if debug is not None:
            msg["attrs"].append(["L2TP_ATTR_DEBUG", debug])

        return self._do_request(msg)

    def create_tunnel(
        self,
        tunnel_id,
        peer_tunnel_id,
        protocol=3,
        remote=None,
        local=None,
        fd=None,
        encap="udp",
        udp_sport=None,
        udp_dport=None,
        udp_csum=None,
        udp6_csum_rx=None,
        udp6_csum_tx=None,
        debug=False,
    ):
        """
        Create a new L2TP tunnel
        :param tunnel_id: local tunnel id
        :param peer_tunnel_id: remote tunnel id
        :param protocol: L2TP version
        :param remote: IP address of the remote peer
        :param local: IP address of the local interface
        :param fd: file descriptor of socket to use
        :param encap: encapsulation type of the tunnel (udp, ip)
        :param udp_sport: UDP source port to be used for the tunnel
        :param udp_dport: UDP destination port to be used for the tunnel
        :param udp_csum: control if IPv4 UDP checksums should be calculated and
                         checked
        :param udp6_csum_rx: control if IPv6 UDP rx checksums should be
                             calculated
        :param udp6_csum_tx: control if IPv6 UDP tx checksums should be
                             calculated
        :param debug: enable or disable debugging using kernel printk for the
                      tunnel
        :return: Netlink response
        """

        if not remote:
            raise ValueError("remote endpoint missing")
        if not local:
            raise ValueError("local endpoint missing")

        if encap == "udp":
            if not udp_sport:
                raise ValueError(
                    "udp_sport is required when UDP encapsulation is "
                    "selected"
                )
            if not udp_dport:
                raise ValueError(
                    "udp_dport is required when UDP encapsulation is "
                    "selected"
                )

        return self._send_tunnel(
            cmd=L2TP_CMD_TUNNEL_CREATE,
            tunnel_id=tunnel_id,
            peer_tunnel_id=peer_tunnel_id,
            protocol=protocol,
            remote=remote,
            local=local,
            fd=fd,
            encap=encap,
            udp_sport=udp_sport,
            udp_dport=udp_dport,
            udp_csum=udp_csum,
            udp6_csum_rx=udp6_csum_rx,
            udp6_csum_tx=udp6_csum_tx,
            debug=debug,
        )

    def modify_tunnel(self, tunnel_id, debug):
        """
        Modify an existing L2TP tunnel
        :param tunnel_id: local tunnel id
        :param debug: enable or disable debugging using kernel printk for the
                      tunnel
        :return: netlink response
        """
        return self._send_tunnel(
            L2TP_CMD_TUNNEL_MODIFY, tunnel_id=tunnel_id, debug=debug
        )

    def delete_tunnel(self, tunnel_id):
        """
        Delete a tunnel
        :param tunnel_id: tunnel id of the tunnel to be deleted
        :return: netlink response
        """
        msg = l2tpmsg()
        msg["cmd"] = L2TP_CMD_TUNNEL_DELETE
        msg["version"] = L2TP_GENL_VERSION
        msg["attrs"].append(["L2TP_ATTR_CONN_ID", tunnel_id])

        return self._do_request(msg)

    def _send_session(
        self,
        cmd,
        tunnel_id,
        session_id,
        peer_session_id=None,
        ifname=None,
        l2spec_type=None,
        cookie=None,
        peer_cookie=None,
        debug=None,
        seq=None,
        lns_mode=None,
        recv_timeout=None,
        pwtype=L2TP_PWTYPE_ETH,
    ):
        """
        Send session create or modify commands
        :param cmd: Netlink command to use
        :param tunnel_id: local tunnel id
        :param session_id: local session id
        :param peer_session_id: remote session id
        :param ifname: interface name
        :param l2spec_type: layer2 specific header type of the session
        :param cookie: local cookie value to be assigned to the session
        :param peer_cookie: remote cookie value to be assigned to the session
        :param debug: enable or disable debugging using kernel printk for the
                      session
        :param seq: controls sequence numbering to prevent or detect out of
                    order packets
        :param lns_mode: LNS mode
        :param recv_timeout: Reorder timeout
        :param pwtype: pseudowire type
        :return: netlink response
        """
        msg = l2tpmsg()
        msg["cmd"] = cmd
        msg["version"] = L2TP_GENL_VERSION
        msg["attrs"].append(["L2TP_ATTR_CONN_ID", tunnel_id])
        msg["attrs"].append(["L2TP_ATTR_SESSION_ID", session_id])
        if cmd == L2TP_CMD_SESSION_CREATE:
            if peer_session_id:
                msg["attrs"].append(
                    ["L2TP_ATTR_PEER_SESSION_ID", peer_session_id]
                )
            else:
                raise ValueError(
                    "peer_session_id required when creating a session"
                )

        if ifname:
            msg["attrs"].append(["L2TP_ATTR_IFNAME", ifname])

        if cmd == L2TP_CMD_SESSION_CREATE:
            if l2spec_type == "none":
                l2spec_type_value = L2TP_L2SPECTYPE_NONE
            else:
                l2spec_type_value = L2TP_L2SPECTYPE_DEFAULT
            msg["attrs"].append(["L2TP_ATTR_L2SPEC_TYPE", l2spec_type_value])

        if cookie:
            if len(cookie) - 2 not in (8, 16):
                raise ValueError("cookie must be either 8 or 16 hex digits")
            msg["attrs"].append(["L2TP_ATTR_COOKIE", cookie])

        if peer_cookie:
            if len(peer_cookie) - 2 not in (8, 16):
                raise ValueError(
                    "peer_cookie must be either 8 or 16 hex digits"
                )
            msg["attrs"].append(["L2TP_ATTR_PEER_COOKIE", peer_cookie])

        if debug is not None:
            msg["attrs"].append(["L2TP_ATTR_DEBUG", debug])

        if seq == "both":
            msg["attrs"].append(["L2TP_ATTR_RECV_SEQ", True])
            msg["attrs"].append(["L2TP_ATTR_SEND_SEQ", True])
        elif seq == "recv":
            msg["attrs"].append(["L2TP_ATTR_RECV_SEQ", True])
        elif seq == "send":
            msg["attrs"].append(["L2TP_ATTR_SEND_SEQ", True])

        if lns_mode:
            msg["attrs"].append(["L2TP_ATTR_LNS_MODE", lns_mode])

        if recv_timeout is not None:
            msg["attrs"].append(["L2TP_ATTR_RECV_TIMEOUT", recv_timeout])

        if cmd == L2TP_CMD_SESSION_CREATE:
            msg["attrs"].append(["L2TP_ATTR_PW_TYPE", pwtype])

        return self._do_request(msg)

    def create_session(
        self,
        tunnel_id,
        session_id,
        peer_session_id=None,
        ifname=None,
        l2spec_type=None,
        cookie=None,
        peer_cookie=None,
        debug=None,
        seq=None,
        lns_mode=None,
        recv_timeout=None,
        pwtype=L2TP_PWTYPE_ETH,
    ):
        """
        Add a new session to a tunnel
        :param tunnel_id: local tunnel id
        :param session_id: local session id
        :param peer_session_id: remote session id
        :param ifname: interface name
        :param l2spec_type: layer2 specific header type of the session
        :param cookie: local cookie value to be assigned to the session
        :param peer_cookie: remote cookie value to be assigned to the session
        :param debug: enable or disable debugging using kernel printk for the
                      session
        :param seq: controls sequence numbering to prevent or detect out of
                    order packets
        :param lns_mode: LNS mode
        :param recv_timeout: Reorder timeout
        :param pwtype: pseudowire type
        :return: netlink response
        """
        self._send_session(
            cmd=L2TP_CMD_SESSION_CREATE,
            tunnel_id=tunnel_id,
            session_id=session_id,
            peer_session_id=peer_session_id,
            ifname=ifname,
            l2spec_type=l2spec_type,
            cookie=cookie,
            peer_cookie=peer_cookie,
            debug=debug,
            seq=seq,
            lns_mode=lns_mode,
            recv_timeout=recv_timeout,
            pwtype=pwtype,
        )

    def modify_session(
        self,
        tunnel_id,
        session_id,
        debug=None,
        seq=None,
        lns_mode=None,
        recv_timeout=None,
    ):
        """
        Modify an existing session
        :param tunnel_id: local tunnel id
        :param session_id: local session id
        :param debug: enable or disable debugging for the session
        :param seq: controls sequence numbering to prevent or detect out of
                    order packets
        :param lns_mode: LNS mode
        :param recv_timeout: Reorder timeout
        :return: netlink response
        """
        self._send_session(
            cmd=L2TP_CMD_SESSION_MODIFY,
            tunnel_id=tunnel_id,
            session_id=session_id,
            debug=debug,
            seq=seq,
            lns_mode=lns_mode,
            recv_timeout=recv_timeout,
        )

    def delete_session(self, tunnel_id, session_id):
        """
        Delete a session
        :param tunnel_id: tunnel id in which the session to be deleted is
                          located
        :param session_id: session id of the session to be deleted
        :return:z
        """
        msg = l2tpmsg()
        msg["cmd"] = L2TP_CMD_SESSION_DELETE
        msg["version"] = L2TP_GENL_VERSION
        msg["attrs"].append(["L2TP_ATTR_CONN_ID", tunnel_id])
        msg["attrs"].append(["L2TP_ATTR_SESSION_ID", session_id])

        return self._do_request(msg)

    def get_tunnel(self, tunnel_id):
        """
        Get one tunnel
        :param tunnel_id: tunnel id of the tunnel to show
        :return: netlink response
        """
        msg = l2tpmsg()
        msg["cmd"] = L2TP_CMD_TUNNEL_GET
        msg["version"] = L2TP_GENL_VERSION
        msg["attrs"].append(["L2TP_ATTR_CONN_ID", tunnel_id])
        return self._do_request(msg, msg_flags=NLM_F_REQUEST)[0]

    def dump_tunnels(self, tunnel_id):
        """
        Dump all tunnels
        :return: netlink response
        """
        msg = l2tpmsg()
        msg["cmd"] = L2TP_CMD_TUNNEL_GET
        msg["version"] = L2TP_GENL_VERSION
        return self._do_request(msg, msg_flags=NLM_F_REQUEST | NLM_F_DUMP)

    def get_session(self, tunnel_id, session_id):
        """
        Get one session
        :param tunnel_id: tunnel id of the session
        :param session_id: session id of the session
        :return: netlink response
        """
        msg = l2tpmsg()
        msg["cmd"] = L2TP_CMD_SESSION_GET
        msg["version"] = L2TP_GENL_VERSION
        msg["attrs"].append(["L2TP_ATTR_CONN_ID", tunnel_id])
        msg["attrs"].append(["L2TP_ATTR_SESSION_ID", session_id])

        return self._do_request(msg, msg_flags=NLM_F_REQUEST)[0]

    def dump_sessions(self):
        """
        Dump all sessions
        :return: netlink response
        """
        msg = l2tpmsg()
        msg["cmd"] = L2TP_CMD_SESSION_GET
        msg["version"] = L2TP_GENL_VERSION

        return self._do_request(msg, msg_flags=NLM_F_REQUEST | NLM_F_DUMP)
