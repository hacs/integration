class cmsg(dict):
    def __init__(self, target, payload=None):
        self['header'] = {'target': target}
        self.payload = payload


class cmsg_event(cmsg):
    pass


class cmsg_failed(cmsg):
    pass


class cmsg_sstart(cmsg):
    pass
