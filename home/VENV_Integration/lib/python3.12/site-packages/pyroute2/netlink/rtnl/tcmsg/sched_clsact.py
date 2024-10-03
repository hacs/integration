'''
clsact
++++++

The clsact qdisc provides a mechanism to attach integrated
filter-action classifiers to an interface, either at ingress or egress,
or both. The use case shown here is using a bpf program (implemented
elsewhere) to direct the packet processing. The example also uses the
direct-action feature to specify what to do with each packet (pass,
drop, redirect, etc.).

BPF ingress/egress example using clsact qdisc::

    # open_bpf_fd is outside the scope of pyroute2
    #fd = open_bpf_fd()
    eth0 = ip.get_links(ifname="eth0")[0]
    ip.tc("add", "clsact", eth0)
    # add ingress clsact
    ip.tc("add-filter", "bpf", idx, ":1", fd=fd, name="myprog",
          parent="ffff:fff2", classid=1, direct_action=True)
    # add egress clsact
    ip.tc("add-filter", "bpf", idx, ":1", fd=fd, name="myprog",
          parent="ffff:fff3", classid=1, direct_action=True)

'''

from pyroute2.netlink.rtnl import TC_H_CLSACT

parent = TC_H_CLSACT


def fix_msg(msg, kwarg):
    msg['handle'] = 0xFFFF0000
