'''
CLI provides a simple syntax to manipulate NDB. The syntax is the
same for the console and the http versions.

The first level of the hierarchy represents NDB views:

* interfaces -- network interfaces
* addresses -- IP addresses
* routes -- IP and MPLS routes, one record per NH
* neighbours -- ARP cache
* rules -- RPDB rules
* netns -- network namespaces
* vlans -- bridge VLAN filters

CLI supports indentation, though it is optional. A level up in the
indentation means a level up in the object hierarchy. Same effect
with `..` command.

An example script to create a bridge and a port, no indentation::

    ; comments start with ;
    interfaces
    create ifname br0, kind bridge
    address 00:11:22:33:44:55
    state up
    add_ip 192.168.123.21/24
    add_ip 192.168.123.22/24
    commit
    .. ; level up to the interfaces view
    create ifname br0p0, kind dummy
    state up
    master br0
    commit

Same script with indentation, no `..` needed::

    interfaces
        create ifname br0, kind bridge
            address 00:11:22:33:44:55
            state up
            add_ip 192.168.123.21/24
            add_ip 192.168.123.22/24
            commit
        create ifname br0p0, kind dummy
            state up
            master br0
            commit

Select objects::

    ; by name
    interfaces br0
        ; ...

    ; by spec
    interfaces
        {target netns01, ifname eth0}
            ; ...
        {address 00:11:22:33:44:55}
            ; ...




Manage interfaces
-----------------

Create::

    interfaces
        create ifname br0.100, kind vlan, vlan_id 100, link br0
            commit
        create ifname v0, kind veth, peer v0p
            commit

Change mac address::

    interfaces br0
        address 00:11:22:33:44:55
        commit

Change netns and rename::

    sources
        add netns test01
    interfaces
        v0p
            net_ns_fd test01
            commit
        {target test01, ifname v0p}
            ifname eth0
            commit
        summary | filter kind veth | select target, ifname | format json

Manage addresses
----------------

...

Manage routes
-------------

...

Generate reports
----------------

It is possible to modify the output of the dump or summary commands::

    interfaces
        ; print index, ifname and MAC address for UP interfaces
        dump | filter state up | select index, ifname, address

    routes
        ; output in JSON format
        summary | format json

The `format` command can only be the last in the sentence. Available
output filters:

filter { } -- filter out records
select { } -- output only selected record fields
format { } -- change the output format, possible values: csv, json

Wait for events
---------------

...

'''

t_stmt = 1
t_dict = 2
t_comma = 3
t_pipe = 4
t_end_of_dict = 7
t_end_of_sentence = 8
t_end_of_stream = 9


def change_pointer(f):
    f.__cli_cptr__ = True
    return f


def show_result(f):
    f.__cli_publish__ = True
    return f
