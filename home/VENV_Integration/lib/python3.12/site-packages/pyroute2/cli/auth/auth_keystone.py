import os
import time

from dateutil.parser import parse as isodate
from keystoneauth1 import session
from keystoneauth1.identity import v3
from keystoneclient.v3 import client as ksclient
from keystoneclient.v3.tokens import TokenManager


class OSAuthManager(object):
    def __init__(self, headers):
        # create a Keystone password object
        auth = v3.Password(
            auth_url=os.environ.get('OS_AUTH_URL'),
            username=os.environ.get('OS_USERNAME'),
            password=os.environ.get('OS_PASSWORD'),
            user_domain_name=(os.environ.get('OS_USER_DOMAIN_NAME')),
            project_id=os.environ.get('OS_PROJECT_ID'),
        )
        # create a session object
        sess = session.Session(auth=auth)
        # create a token manager
        tmanager = TokenManager(ksclient.Client(session=sess))
        # validate the token
        keystone_response = tmanager.validate(headers['X-Auth-Token'])
        # init attrs
        self.expire = isodate(keystone_response['expires_at']).timestamp()

    def check(self, obj, tag):
        if time.time() > self.expire:
            raise PermissionError('keystone token has been expired')
        return True
