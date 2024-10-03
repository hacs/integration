from socket import AF_INET, inet_ntop, inet_pton

from pyroute2.dhcp import dhcpmsg, option


class dhcp4msg(dhcpmsg):
    #
    # https://www.ietf.org/rfc/rfc2131.txt
    #
    fields = (
        ('op', 'uint8', 1),  # request
        ('htype', 'uint8', 1),  # ethernet
        ('hlen', 'uint8', 6),  # ethernet addr len
        ('hops', 'uint8'),
        ('xid', 'uint32'),
        ('secs', 'uint16'),
        ('flags', 'uint16'),
        ('ciaddr', 'ip4addr'),
        ('yiaddr', 'ip4addr'),
        ('siaddr', 'ip4addr'),
        ('giaddr', 'ip4addr'),
        ('chaddr', 'l2paddr'),
        ('sname', '64s'),
        ('file', '128s'),
        ('cookie', '4s', b'c\x82Sc'),
    )
    #
    # https://www.ietf.org/rfc/rfc2132.txt
    #
    options = (
        (0, 'pad', 'none'),
        (1, 'subnet_mask', 'ip4addr'),
        (2, 'time_offset', 'be32'),
        (3, 'router', 'ip4list'),
        (4, 'time_server', 'ip4list'),
        (5, 'ien_name_server', 'ip4list'),
        (6, 'name_server', 'ip4list'),
        (7, 'log_server', 'ip4list'),
        (8, 'cookie_server', 'ip4list'),
        (9, 'lpr_server', 'ip4list'),
        (50, 'requested_ip', 'ip4addr'),
        (51, 'lease_time', 'be32'),
        (53, 'message_type', 'uint8'),
        (54, 'server_id', 'ip4addr'),
        (55, 'parameter_list', 'array8'),
        (57, 'messagi_size', 'be16'),
        (58, 'renewal_time', 'be32'),
        (59, 'rebinding_time', 'be32'),
        (60, 'vendor_id', 'string'),
        (61, 'client_id', 'client_id'),
        (255, 'end', 'none'),
    )

    class ip4addr(option):
        policy = {
            'format': '4s',
            'encode': lambda x: inet_pton(AF_INET, x),
            'decode': lambda x: inet_ntop(AF_INET, x),
        }

    class ip4list(option):
        policy = {
            'format': 'string',
            'encode': lambda x: ''.join([inet_pton(AF_INET, i) for i in x]),
            'decode': lambda x: [
                inet_ntop(AF_INET, x[i * 4 : i * 4 + 4])
                for i in range(len(x) // 4)
            ],
        }
