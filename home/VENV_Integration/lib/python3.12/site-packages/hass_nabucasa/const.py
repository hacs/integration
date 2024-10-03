"""Constants for the hass-nabucasa."""

from __future__ import annotations

CONFIG_DIR = ".cloud"

REQUEST_TIMEOUT = 10

MODE_PROD = "production"
MODE_DEV = "development"

STATE_CONNECTING = "connecting"
STATE_CONNECTED = "connected"
STATE_DISCONNECTED = "disconnected"

DISPATCH_REMOTE_CONNECT = "remote_connect"
DISPATCH_REMOTE_DISCONNECT = "remote_disconnect"
DISPATCH_REMOTE_BACKEND_UP = "remote_backend_up"
DISPATCH_REMOTE_BACKEND_DOWN = "remote_backend_down"

DEFAULT_SERVERS: dict[str, dict[str, str]] = {
    "production": {
        "account_link": "account-link.nabucasa.com",
        "accounts": "accounts.nabucasa.com",
        "acme": "acme-v02.api.letsencrypt.org",
        "alexa": "alexa-api.nabucasa.com",
        "cloudhook": "webhooks-api.nabucasa.com",
        "relayer": "cloud.nabucasa.com",
        "remotestate": "remotestate.nabucasa.com",
        "servicehandlers": "servicehandlers.nabucasa.com",
        "thingtalk": "thingtalk-api.nabucasa.com",
    },
    "development": {},
}

DEFAULT_VALUES: dict[str, dict[str, str]] = {
    "production": {
        "cognito_client_id": "60i2uvhvbiref2mftj7rgcrt9u",
        "user_pool_id": "us-east-1_87ll5WOP8",
        "region": "us-east-1",
    },
    "development": {},
}

MESSAGE_EXPIRATION = """
It looks like your Home Assistant Cloud subscription has expired. Please check
your [account page](/config/cloud/account) to continue using the service.
"""

MESSAGE_AUTH_FAIL = """
You have been logged out of Home Assistant Cloud because we have been unable
to verify your credentials. Please [log in](/config/cloud) again to continue
using the service.
"""

MESSAGE_REMOTE_READY = """
Your remote access is now available.
You can manage your connectivity on the
[Cloud panel](/config/cloud) or with our [portal](https://account.nabucasa.com/).
"""

MESSAGE_REMOTE_SETUP = """
Unable to create a certificate. We will automatically
retry it and notify you when it's available.
"""

MESSAGE_LOAD_CERTIFICATE_FAILURE = """
Unable to load the certificate. We will automatically
recreate it and notify you when it's available.
"""
