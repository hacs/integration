def ipdb_interfaces_view(ndb):
    '''Provide read-only interfaces view with IPDB layout.

    In addition to standard NDB fields provides some IPDB
    specific fields.

    The method returns a simple dict structure, no background
    updates or system changes are supported.

    Please open a ticket on the project page if you are
    missing any attribute used in your project:

    https://github.com/svinota/pyroute2/issues
    '''
    ret = {}

    for record in ndb.interfaces.dump():
        interface = record._as_dict()
        interface['ipdb_scope'] = 'system'
        interface['ipdb_priority'] = 0
        try:
            interface['ipaddr'] = tuple(
                (
                    (x.address, x.prefixlen)
                    for x in (
                        ndb.addresses.dump().select_records(index=record.index)
                    )
                )
            )
        except:
            with ndb.addresses.summary() as report:
                report.select_records(ifname=f"{record.ifname}")
                interface['ipaddr'] = tuple(
                    ((x.address, x.prefixlen) for x in report)
                )
        try:
            interface['ports'] = tuple(
                (
                    x.index
                    for x in (
                        ndb.interfaces.dump().select_records(
                            master=record.index
                        )
                    )
                )
            )
        except:
            with ndb.interfaces.dump() as report:
                report.select_records(ifname=f"{record.ifname}")
                interface['ports'] = tuple((x.index for x in report))
        try:
            interface['neighbours'] = tuple(
                (
                    x.dst
                    for x in (
                        ndb.neighbours.dump().select_records(
                            ifindex=record.index
                        )
                    )
                )
            )
        except:
            with ndb.neighbours.dump() as report:
                report.select_records(ifindex=record.index)
                interface['neighbours'] = tuple((x.dst for x in report))
        ret[record.ifname] = interface

    return ret
