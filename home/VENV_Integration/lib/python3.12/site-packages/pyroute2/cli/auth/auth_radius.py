import os

import pyrad.packet
from pyrad.client import Client
from pyrad.dictionary import Dictionary


class RadiusAuthManager(object):
    def __init__(self, headers):
        user = headers['X-Auth-User']
        password = headers['X-Auth-Password']

        client = Client(
            server=os.environ.get('RADIUS_SERVER'),
            secret=os.environ.get('RADIUS_SECRET').encode('ascii'),
            dict=Dictionary('dictionary'),
        )

        req = client.CreateAuthPacket(
            code=pyrad.packet.AccessRequest, User_Name=user
        )

        req['User-Password'] = req.PwCrypt(password)
        reply = client.SendPacket(req)
        self.auth = reply.code

    def check(self, obj, tag):
        return self.auth == pyrad.packet.AccessAccept
