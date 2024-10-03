from enum import Enum

import requests.auth
import requests

from . import Cognito


class TokenType(str, Enum):
    ID_TOKEN = "id_token"
    ACCESS_TOKEN = "access_token"


class RequestsSrpAuth(requests.auth.AuthBase):
    """
    A Requests Auth Plugin to automatically populate Authorization header
    with a Cognito token.

    Example:

    ```
    import requests
    from pycognito.utils import RequestsSrpAuth

    auth = RequestsSrpAuth(
        username='myusername',
        password='secret',
        user_pool_id='eu-west-1_1234567',
        client_id='4dn6jbcbhqcofxyczo3ms9z4cc',
        user_pool_region='eu-west-1',
    )

    response = requests.get('http://test.com', auth=auth)
    ```
    """

    def __init__(
        self,
        username: str = None,
        password: str = None,
        user_pool_id: str = None,
        user_pool_region: str = None,
        client_id: str = None,
        cognito: Cognito = None,
        http_header: str = "Authorization",
        http_header_prefix: str = "Bearer ",
        auth_token_type: TokenType = TokenType.ACCESS_TOKEN,
        boto3_client_kwargs=None,
    ):
        """

        :param username: Cognito User. Required if `cognito` not set
        :param password: Password of Cognito User. Required if `cognito` not set
        :param user_pool_id: Cognito User Pool. Required if `cognito` not set
        :param user_pool_region: Region of the Cognito User Pool. Required if `cognito` not set
        :param client_id: Cognito Client ID / Application. Required if :py:attr:`cognito` not set
        :param cognito: Provide a preconfigured `pycognito.Cognito` instead of `username`, `password` etc
        :param http_header: The HTTP Header to populate. Defaults to "Authorization" (Basic Authentication)
        :param http_header_prefix: Prefix a value before the token. Defaults to "Bearer ". (Note the space)
        :param auth_token_type: Whether to populate the header with ID or ACCESS_TOKEN. Defaults to "ACCESS_TOKEN"
        :param boto3_client_kwargs: Keyword args to pass to Boto3 for client creation
        """

        if cognito:
            self.cognito_client = cognito
        else:
            self.cognito_client = Cognito(
                user_pool_id=user_pool_id,
                client_id=client_id,
                user_pool_region=user_pool_region,
                username=username,
                boto3_client_kwargs=boto3_client_kwargs,
            )

        self.username = username
        self.__password = password
        self.http_header = http_header
        self.http_header_prefix = http_header_prefix
        self.token_type = auth_token_type

    def __call__(self, request: requests.Request):
        # If this is the first time in, we'll need to auth
        if not self.cognito_client.access_token:
            self.cognito_client.authenticate(password=self.__password)

        # Checks if token is expired and fetches a new token if available
        self.cognito_client.check_token(renew=True)

        token = getattr(self.cognito_client, self.token_type.value)

        request.headers[self.http_header] = self.http_header_prefix + token

        return request
