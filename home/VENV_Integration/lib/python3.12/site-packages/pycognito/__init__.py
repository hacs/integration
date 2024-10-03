import ast
import base64
import datetime
import re

import boto3
from envs import env
import jwt
import requests

from .aws_srp import AWSSRP
from .exceptions import TokenVerificationException, MFAChallengeException


def cognito_to_dict(attr_list, attr_map=None):
    if attr_map is None:
        attr_map = {}
    attr_dict = {}
    for attr in attr_list:
        name = attr.get("Name")
        value = attr.get("Value")
        if value in ["true", "false"]:
            value = ast.literal_eval(value.capitalize())
        name = attr_map.get(name, name)
        attr_dict[name] = value
    return attr_dict


def dict_to_cognito(attributes, attr_map=None):
    """
    :param attributes: Dictionary of User Pool attribute names/values
    :return: list of User Pool attribute formatted dicts: {'Name': <attr_name>, 'Value': <attr_value>}
    """
    if attr_map is None:
        attr_map = {}
    for key, value in attr_map.items():
        if value in attributes.keys():
            attributes[key] = attributes.pop(value)

    def normalize(val):
        if isinstance(val, bool):
            return "true" if val else "false"
        return val

    return [
        {"Name": key, "Value": normalize(value)} for key, value in attributes.items()
    ]


def camel_to_snake(camel_str):
    """
    :param camel_str: string
    :return: string converted from a CamelCase to a snake_case
    """
    return re.sub(
        "([a-z0-9])([A-Z])", r"\1_\2", re.sub("(.)([A-Z][a-z]+)", r"\1_\2", camel_str)
    ).lower()


def snake_to_camel(snake_str):
    """
    :param snake_str: string
    :return: string converted from a snake_case to a CamelCase
    """
    components = snake_str.split("_")
    return "".join(x.title() for x in components)


class UserObj:
    def __init__(
        self, username, attribute_list, cognito_obj, metadata=None, attr_map=None
    ):
        """
        :param username:
        :param attribute_list:
        :param metadata: Dictionary of User metadata
        """
        self.username = username
        self._cognito = cognito_obj
        self._attr_map = {} if attr_map is None else attr_map
        self._data = cognito_to_dict(attribute_list, self._attr_map)
        self.sub = self._data.pop("sub", None)
        self.email_verified = self._data.pop("email_verified", None)
        self.phone_number_verified = self._data.pop("phone_number_verified", None)
        self._metadata = {} if metadata is None else metadata

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.__unicode__()}>"

    def __unicode__(self):
        return self.username

    def __getattr__(self, name):
        if name in list(self.__dict__.get("_data", {}).keys()):
            return self._data.get(name)
        if name in list(self.__dict__.get("_metadata", {}).keys()):
            return self._metadata.get(name)
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in list(self.__dict__.get("_data", {}).keys()):
            self._data[name] = value
        else:
            super().__setattr__(name, value)

    def save(self, admin=False):
        if admin:
            self._cognito.admin_update_profile(self._data, self._attr_map)
            return
        self._cognito.update_profile(self._data, self._attr_map)

    def delete(self, admin=False):
        if admin:
            self._cognito.admin_delete_user()
            return
        self._cognito.delete_user()


class GroupObj:
    def __init__(self, group_data, cognito_obj):
        """
        :param group_data: a dictionary with information about a group
        :param cognito_obj: an instance of the Cognito class
        """
        self._data = group_data
        self._cognito = cognito_obj
        self.group_name = self._data.pop("GroupName", None)
        self.description = self._data.pop("Description", None)
        self.creation_date = self._data.pop("CreationDate", None)
        self.last_modified_date = self._data.pop("LastModifiedDate", None)
        self.role_arn = self._data.pop("RoleArn", None)
        self.precedence = self._data.pop("Precedence", None)

    def __unicode__(self):
        return self.group_name

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.__unicode__()}>"


class Cognito:

    user_class = UserObj
    group_class = GroupObj

    def __init__(
        self,
        user_pool_id,
        client_id,
        user_pool_region=None,
        username=None,
        id_token=None,
        refresh_token=None,
        access_token=None,
        client_secret=None,
        access_key=None,
        secret_key=None,
        session=None,
        botocore_config=None,
        boto3_client_kwargs=None,
    ):
        """
        :param user_pool_id: Cognito User Pool ID
        :param client_id: Cognito User Pool Application client ID
        :param username: User Pool username
        :param id_token: ID Token returned by authentication
        :param refresh_token: Refresh Token returned by authentication
        :param access_token: Access Token returned by authentication
        :param access_key: AWS IAM access key
        :param secret_key: AWS IAM secret key
        :param session: Boto3 client session
        :param botocore_config: Botocore Config object for the client
        :param boto3_client_kwargs: Keyword args to pass to Boto3 for client creation
        """

        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.user_pool_region = (
            user_pool_region if user_pool_region else self.user_pool_id.split("_")[0]
        )
        self.username = username
        self.id_token = id_token
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_secret = client_secret
        self.token_type = None
        self.id_claims = None
        self.access_claims = None
        self.custom_attributes = None
        self.base_attributes = None
        self.pool_jwk = None
        self.mfa_tokens = None

        if not boto3_client_kwargs:
            boto3_client_kwargs = {}
        if access_key and secret_key:
            boto3_client_kwargs["aws_access_key_id"] = access_key
            boto3_client_kwargs["aws_secret_access_key"] = secret_key
        self.pool_domain_url = boto3_client_kwargs.get("endpoint_url", None)

        if self.user_pool_region:
            boto3_client_kwargs["region_name"] = self.user_pool_region
        if botocore_config:
            boto3_client_kwargs["config"] = botocore_config

        if session:
            self.client = session.client("cognito-idp", **boto3_client_kwargs)
        else:
            self.client = boto3.client("cognito-idp", **boto3_client_kwargs)

    @property
    def user_pool_url(self):
        if self.pool_domain_url:
            return f"{self.pool_domain_url}/{self.user_pool_id}"

        return f"https://cognito-idp.{self.user_pool_region}.amazonaws.com/{self.user_pool_id}"

    def get_keys(self):
        if self.pool_jwk:
            return self.pool_jwk

        # Check for the dictionary in environment variables.
        pool_jwk_env = env("COGNITO_JWKS", {}, var_type="dict")
        if pool_jwk_env:
            self.pool_jwk = pool_jwk_env
        # If it is not there use the requests library to get it
        else:
            self.pool_jwk = requests.get(
                f"{self.user_pool_url}/.well-known/jwks.json", timeout=15
            ).json()
        return self.pool_jwk

    def get_key(self, kid):
        keys = self.get_keys().get("keys")
        key = list(filter(lambda x: x.get("kid") == kid, keys))
        return key[0]

    def verify_tokens(self):
        """
        Verify the current id_token and access_token.  An exception will be
        thrown if they do not pass verification.  It can be useful to call this
        method after creating a Cognito instance where you've provided
        externally-remembered token values.
        """
        self.verify_token(self.id_token, "id_token", "id")
        self.verify_token(self.access_token, "access_token", "access")

    def verify_token(self, token, id_name, token_use):
        # https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html

        kid = jwt.get_unverified_header(token).get("kid")
        hmac_key = jwt.api_jwk.PyJWK(self.get_key(kid)).key
        required_claims = (["aud"] if token_use != "access" else []) + ["iss", "exp"]
        try:
            decoded = jwt.api_jwt.decode_complete(
                token,
                hmac_key,
                algorithms=["RS256"],
                audience=self.client_id if token_use != "access" else None,
                issuer=self.user_pool_url,
                options={
                    "require": required_claims,
                    "verify_iat": False,
                },
            )
        except jwt.PyJWTError as err:
            raise TokenVerificationException(
                f"Your {id_name!r} token could not be verified ({err})."
            ) from None
        verified, header = decoded["payload"], decoded["header"]

        token_use_verified = verified.get("token_use") == token_use
        if not token_use_verified:
            raise TokenVerificationException(
                f"Your {id_name!r} token use ({token_use!r}) could not be verified."
            )

        if (iat := verified.get("iat")) is not None:
            try:
                int(iat)
            except ValueError as execption:
                raise TokenVerificationException(
                    f"Your {id_name!r} token's iat claim is not a valid integer."
                ) from execption

        # Compute and verify at_hash (formerly done by python-jose)
        if "at_hash" in verified:
            alg_obj = jwt.get_algorithm_by_name(header["alg"])
            digest = alg_obj.compute_hash_digest(self.access_token)
            at_hash = base64.urlsafe_b64encode(digest[: (len(digest) // 2)]).rstrip("=")
            if at_hash != verified["at_hash"]:
                raise TokenVerificationException(
                    "at_hash claim does not match access_token."
                )

        setattr(self, id_name, token)
        setattr(self, f"{token_use}_claims", verified)
        return verified

    def get_user_obj(
        self, username=None, attribute_list=None, metadata=None, attr_map=None
    ):
        """
        Returns the specified user
        :param username: Username of the user
        :param attribute_list: List of tuples that represent the user's
            attributes as returned by the admin_get_user or get_user boto3 methods
        :param metadata: Metadata about the user
        :param attr_map: Dictionary that maps the Cognito attribute names to
        what we'd like to display to the users
        :return: dictionary of the Cognito user response
        """
        return self.user_class(
            username=username,
            attribute_list=attribute_list,
            cognito_obj=self,
            metadata=metadata,
            attr_map=attr_map,
        )

    def get_group_obj(self, group_data):
        """
        Instantiates the self.group_class
        :param group_data: a dictionary with information about a group
        :return: an instance of the self.group_class
        """
        return self.group_class(group_data=group_data, cognito_obj=self)

    def switch_session(self, session):
        """
        Primarily used for unit testing so we can take advantage of the
        placebo library (https://githhub.com/garnaat/placebo)
        :param session: boto3 session
        :return:
        """
        self.client = session.client("cognito-idp")

    def check_token(self, renew=True):
        """
        Checks the exp attribute of the access_token and either refreshes
        the tokens by calling the renew_access_tokens method or does nothing
        :param renew: bool indicating whether to refresh on expiration
        :return: bool indicating whether access_token has expired
        """
        if not self.access_token:
            raise AttributeError("Access Token Required to Check Token")
        now = datetime.datetime.now()
        dec_access_token = jwt.decode(
            self.access_token, options={"verify_signature": False}
        )

        if now > datetime.datetime.fromtimestamp(dec_access_token["exp"]):
            expired = True
            if renew:
                self.renew_access_token()
        else:
            expired = False
        return expired

    def set_base_attributes(self, **kwargs):
        self.base_attributes = kwargs

    def add_custom_attributes(self, **kwargs):
        custom_key = "custom"
        custom_attributes = {}

        for old_key, value in kwargs.items():
            new_key = custom_key + ":" + old_key
            custom_attributes[new_key] = value

        self.custom_attributes = custom_attributes

    def register(self, username, password, attr_map=None, client_metadata=None):
        """
        Register the user. Other base attributes from AWS Cognito User Pools
        are address, birthdate, email, family_name (last name), gender,
        given_name (first name), locale, middle_name, name, nickname,
        phone_number, picture, preferred_username, profile, zoneinfo,
        updated at, website
        :param username: User Pool username
        :param password: User Pool password
        :param attr_map: Attribute map to Cognito's attributes
        :param client_metadata: Metadata about the user that will be used for ClientMetadata
        :return response: Response from Cognito

        Example response::
        {
            'UserConfirmed': True|False,
            'CodeDeliveryDetails': {
                'Destination': 'string', # This value will be obfuscated
                'DeliveryMedium': 'SMS'|'EMAIL',
                'AttributeName': 'string'
            }
        }
        """
        if self.base_attributes is None:
            attributes = {}
        else:
            attributes = self.base_attributes.copy()
        if self.custom_attributes:
            attributes.update(self.custom_attributes)

        cognito_attributes = dict_to_cognito(attributes, attr_map)
        params = {
            "ClientId": self.client_id,
            "Username": username,
            "Password": password,
            "UserAttributes": cognito_attributes,
        }
        if client_metadata is not None:
            params["ClientMetadata"] = client_metadata
        self._add_secret_hash(params, "SecretHash")
        response = self.client.sign_up(**params)

        attributes.update(username=username, password=password)
        self._set_attributes(response, attributes)

        response.pop("ResponseMetadata")
        return response

    def admin_confirm_sign_up(self, username=None):
        """
        Confirms user registration as an admin without using a confirmation
        code. Works on any user.
        :param username: User's username
        :return:
        """
        if not username:
            username = self.username
        self.client.admin_confirm_sign_up(
            UserPoolId=self.user_pool_id,
            Username=username,
        )

    def confirm_sign_up(self, confirmation_code, username=None):
        """
        Using the confirmation code that is either sent via email or text
        message.
        :param confirmation_code: Confirmation code sent via text or email
        :param username: User's username
        :return:
        """
        if not username:
            username = self.username
        params = {
            "ClientId": self.client_id,
            "Username": username,
            "ConfirmationCode": confirmation_code,
        }
        self._add_secret_hash(params, "SecretHash")
        self.client.confirm_sign_up(**params)

    def resend_confirmation_code(self, username):
        """
         Trigger resending the confirmation code message.
        :param username: User's username
        :return:
        """
        params = {
            "ClientId": self.client_id,
            "Username": username,
        }
        self._add_secret_hash(params, "SecretHash")
        self.client.resend_confirmation_code(**params)

    def admin_authenticate(self, password):
        """
        Authenticate the user using admin super privileges
        :param password: User's password
        :return:
        """
        auth_params = {"USERNAME": self.username, "PASSWORD": password}
        self._add_secret_hash(auth_params, "SECRET_HASH")
        tokens = self.client.admin_initiate_auth(
            UserPoolId=self.user_pool_id,
            ClientId=self.client_id,
            # AuthFlow='USER_SRP_AUTH'|'REFRESH_TOKEN_AUTH'|'REFRESH_TOKEN'|'CUSTOM_AUTH'|'ADMIN_NO_SRP_AUTH',
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters=auth_params,
        )
        self._set_tokens(tokens)

    def authenticate(self, password, client_metadata=None):
        """
        Authenticate the user using the SRP protocol
        :param password: The user's passsword
        :param client_metadata: Metadata you can provide for custom workflows that RespondToAuthChallenge triggers.
        :return:
        """
        aws = AWSSRP(
            username=self.username,
            password=password,
            pool_id=self.user_pool_id,
            client_id=self.client_id,
            client=self.client,
            client_secret=self.client_secret,
        )
        try:
            tokens = aws.authenticate_user(client_metadata=client_metadata)
        except MFAChallengeException as mfa_challenge:
            self.mfa_tokens = mfa_challenge.get_tokens()
            raise mfa_challenge

        self._set_tokens(tokens)

    def new_password_challenge(self, password, new_password):
        """
        Respond to the new password challenge using the SRP protocol
        :param password: The user's current passsword
        :param password: The user's new passsword
        """
        aws = AWSSRP(
            username=self.username,
            password=password,
            pool_id=self.user_pool_id,
            client_id=self.client_id,
            client=self.client,
            client_secret=self.client_secret,
        )
        tokens = aws.set_new_password_challenge(new_password)
        self._set_tokens(tokens)

    def logout(self):
        """
        Logs the user out of all clients and removes the expires_in,
        expires_datetime, id_token, refresh_token, access_token, and token_type
        attributes
        :return:
        """
        self.client.global_sign_out(AccessToken=self.access_token)

        self.id_token = None
        self.refresh_token = None
        self.access_token = None
        self.token_type = None

    def admin_update_profile(self, attrs, attr_map=None):
        user_attrs = dict_to_cognito(attrs, attr_map)
        self.client.admin_update_user_attributes(
            UserPoolId=self.user_pool_id,
            Username=self.username,
            UserAttributes=user_attrs,
        )

    def update_profile(self, attrs, attr_map=None):
        """
        Updates User attributes
        :param attrs: Dictionary of attribute name, values
        :param attr_map: Dictionary map from Cognito attributes to attribute
        names we would like to show to our users
        """
        user_attrs = dict_to_cognito(attrs, attr_map)
        self.client.update_user_attributes(
            UserAttributes=user_attrs, AccessToken=self.access_token
        )

    def get_user(self, attr_map=None):
        """
        Returns a UserObj (or whatever the self.user_class is) by using the
        user's access token.
        :param attr_map: Dictionary map from Cognito attributes to attribute
        names we would like to show to our users
        :return: UserObj dictionary
        """
        user = self.client.get_user(AccessToken=self.access_token)

        user_metadata = {
            "username": user.get("Username"),
            "id_token": self.id_token,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
        }
        return self.get_user_obj(
            username=self.username,
            attribute_list=user.get("UserAttributes"),
            metadata=user_metadata,
            attr_map=attr_map,
        )

    def get_users(self, attr_map=None):
        """
        Returns all users for a user pool. Returns instances of the
        self.user_class.
        :param attr_map: Dictionary map from Cognito attributes to attribute
        names we would like to show to our users
        :return: list of self.user_class
        """
        response = self.client.list_users(UserPoolId=self.user_pool_id)
        user_list = response.get("Users")
        page_token = response.get("PaginationToken")

        while page_token:
            response = self.client.list_users(
                UserPoolId=self.user_pool_id, PaginationToken=page_token
            )
            user_list.extend(response.get("Users"))
            page_token = response.get("PaginationToken")

        return [
            self.get_user_obj(
                user.get("Username"),
                attribute_list=user.get("Attributes"),
                metadata={"username": user.get("Username")},
                attr_map=attr_map,
            )
            for user in user_list
        ]

    def admin_get_user(self, attr_map=None):
        """
        Get the user's details using admin super privileges.
        :param attr_map: Dictionary map from Cognito attributes to attribute
        names we would like to show to our users
        :return: UserObj dictionary
        """
        user = self.client.admin_get_user(
            UserPoolId=self.user_pool_id, Username=self.username
        )
        user_metadata = {
            "enabled": user.get("Enabled"),
            "user_status": user.get("UserStatus"),
            "username": user.get("Username"),
            "create_date": user.get("UserCreateDate"),
            "modified_date": user.get("UserLastModifiedDate"),
            "id_token": self.id_token,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
        }
        return self.get_user_obj(
            username=self.username,
            attribute_list=user.get("UserAttributes"),
            metadata=user_metadata,
            attr_map=attr_map,
        )

    def admin_create_user(
        self,
        username,
        temporary_password="",
        additional_kwargs=None,
        attr_map=None,
        **kwargs,
    ):
        """
        Create a user using admin super privileges.
        :param username: User Pool username
        :param temporary_password: The temporary password to give the user.
        Pass None or omit this to make Cognito generate a temporary password for the user.
        :param additional_kwargs: Dictionary with request params, such as MessageAction.
        :param attr_map: Attribute map to Cognito's attributes
        :param kwargs: Additional User Pool attributes
        :return response: Response from Cognito
        """
        if additional_kwargs is None:
            additional_kwargs = {}
        if temporary_password:
            additional_kwargs["TemporaryPassword"] = temporary_password
        response = self.client.admin_create_user(
            UserPoolId=self.user_pool_id,
            Username=username,
            UserAttributes=dict_to_cognito(kwargs, attr_map),
            **additional_kwargs,
        )
        kwargs.update(username=username)
        self._set_attributes(response, kwargs)

        response.pop("ResponseMetadata")
        return response

    def send_verification(self, attribute="email"):
        """
        Sends the user an attribute verification code for the specified attribute name.
        :param attribute: Attribute to confirm. Defaults to "email"
        """
        self.check_token()
        self.client.get_user_attribute_verification_code(
            AccessToken=self.access_token, AttributeName=attribute
        )

    def validate_verification(self, confirmation_code, attribute="email"):
        """
        Verifies the specified user attributes in the user pool.
        :param confirmation_code: Code sent to user upon intiating verification
        :param attribute: Attribute to confirm. Defaults to "email"
        """
        self.check_token()
        return self.client.verify_user_attribute(
            AccessToken=self.access_token,
            AttributeName=attribute,
            Code=confirmation_code,
        )

    def renew_access_token(self):
        """
        Sets a new access token on the User using the cached refresh token.
        """
        auth_params = {"REFRESH_TOKEN": self.refresh_token}
        self._add_secret_hash(auth_params, "SECRET_HASH")
        refresh_response = self.client.initiate_auth(
            ClientId=self.client_id,
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters=auth_params,
        )
        self._set_tokens(refresh_response)

    def initiate_forgot_password(self):
        """
        Sends a verification code to the user to use to change their password.
        """
        params = {"ClientId": self.client_id, "Username": self.username}
        self._add_secret_hash(params, "SecretHash")
        self.client.forgot_password(**params)

    def delete_user(self):
        self.client.delete_user(AccessToken=self.access_token)

    def admin_delete_user(self):
        self.client.admin_delete_user(
            UserPoolId=self.user_pool_id, Username=self.username
        )

    def admin_reset_password(self, username, client_metadata=None):
        if client_metadata is None:
            client_metadata = {}
        self.client.admin_reset_user_password(
            UserPoolId=self.user_pool_id,
            Username=username,
            ClientMetadata=client_metadata,
        )

    def confirm_forgot_password(self, confirmation_code, password):
        """
        Allows a user to provide their verification code and choose a new password.
        :param confirmation_code: The confirmation code sent by a user's request
        to retrieve a forgotten password
        :param password: New password
        """
        params = {
            "ClientId": self.client_id,
            "Username": self.username,
            "ConfirmationCode": confirmation_code,
            "Password": password,
        }
        self._add_secret_hash(params, "SecretHash")
        response = self.client.confirm_forgot_password(**params)
        self._set_attributes(response, {"password": password})

    def change_password(self, previous_password, proposed_password):
        """
        Change the User password
        """
        self.check_token()
        response = self.client.change_password(
            PreviousPassword=previous_password,
            ProposedPassword=proposed_password,
            AccessToken=self.access_token,
        )
        self._set_attributes(response, {"password": proposed_password})

    def _add_secret_hash(self, parameters, key):
        """
        Helper function that computes SecretHash and adds it
        to a parameters dictionary at a specified key
        """
        if self.client_secret is not None:
            secret_hash = AWSSRP.get_secret_hash(
                self.username, self.client_id, self.client_secret
            )
            parameters[key] = secret_hash

    def _set_tokens(self, tokens):
        """
        Helper function to verify and set token attributes based on a Cognito
        AuthenticationResult.
        """
        self.verify_token(
            tokens["AuthenticationResult"]["AccessToken"], "access_token", "access"
        )
        self.verify_token(tokens["AuthenticationResult"]["IdToken"], "id_token", "id")
        if "RefreshToken" in tokens["AuthenticationResult"]:
            self.refresh_token = tokens["AuthenticationResult"]["RefreshToken"]
        self.token_type = tokens["AuthenticationResult"]["TokenType"]

    def _set_attributes(self, response, attribute_dict):
        """
        Set user attributes based on response code
        :param response: HTTP response from Cognito
        :param attribute_dict: Dictionary of attribute names and values
        """
        status_code = response.get(
            "HTTPStatusCode", response["ResponseMetadata"]["HTTPStatusCode"]
        )
        if status_code == 200:
            for key, value in attribute_dict.items():
                setattr(self, key, value)

    def get_group(self, group_name):
        """
        Get a group by name
        :param group_name: name of a group
        :return: instance of the self.group_class
        """
        response = self.client.get_group(
            GroupName=group_name, UserPoolId=self.user_pool_id
        )
        return self.get_group_obj(response.get("Group"))

    def get_groups(self):
        """
        Returns all groups for a user pool.
        :return: list of instances of self.group_class
        """
        response = self.client.list_groups(UserPoolId=self.user_pool_id)
        return [self.get_group_obj(group_data) for group_data in response.get("Groups")]

    def admin_add_user_to_group(self, username, group_name):
        """
        Add the user to the specified group
        :param username: the username
        :param group_name: the name of the group to add the user to
        :return:
        """
        self.client.admin_add_user_to_group(
            UserPoolId=self.user_pool_id,
            Username=username,
            GroupName=group_name,
        )

    def admin_remove_user_from_group(self, username, group_name):
        """
        Remove the user from the specified group
        :param username: the username
        :param group_name: the name of the group to remove the user from
        :return:
        """
        self.client.admin_remove_user_from_group(
            UserPoolId=self.user_pool_id,
            Username=username,
            GroupName=group_name,
        )

    def admin_list_groups_for_user(self, username):
        """
        Get the list of groups a user belongs to
        :param username:
        :return: List of group objects
        """

        def process_groups_response(groups_response):
            groups = []
            for group_dict in groups_response["Groups"]:
                groups.append(group_dict["GroupName"])
            return groups

        groups_response = self.client.admin_list_groups_for_user(
            Username=username, UserPoolId=self.user_pool_id, Limit=60
        )
        user_groups = process_groups_response(groups_response)

        while "NextToken" in groups_response.keys():
            groups_response = self.client.admin_list_groups_for_user(
                Username=username,
                UserPoolId=self.user_pool_id,
                Limit=60,
                NextToken=groups_response["NextToken"],
            )
            new_groups = process_groups_response(groups_response)
            user_groups.extend(new_groups)

        return user_groups

    def admin_enable_user(self, username):
        """
        Enable a user
        :param username:
        :return:
        """
        self.client.admin_enable_user(
            UserPoolId=self.user_pool_id,
            Username=username,
        )

    def admin_disable_user(self, username):
        """
        Disable a user
        :param username:
        :return:
        """
        self.client.admin_disable_user(
            UserPoolId=self.user_pool_id,
            Username=username,
        )

    def admin_create_identity_provider(
        self, pool_id, provider_name, provider_type, provider_details, **kwargs
    ):
        """
        Creates an identity provider
        :param pool_id: The user pool ID
        :param provider_name: The identity provider name
        :param provider_type: The identity provider type
        :param provider_details: The identity provider details
        :return:
        """
        self.client.create_identity_provider(
            UserPoolId=pool_id,
            ProviderName=provider_name,
            ProviderType=provider_type,
            ProviderDetails=provider_details,
            **kwargs,
        )

    def admin_describe_identity_provider(self, pool_id, provider_name):
        """
        Describes an existing identity provider
        :param pool_id: The user pool ID
        :param provider_name: The identity provider name
        :return: dict of identity provider
        """
        return self.client.describe_identity_provider(
            UserPoolId=pool_id, ProviderName=provider_name
        )

    def admin_update_identity_provider(self, pool_id, provider_name, **kwargs):
        """
        Updates an existing identity provider
        :param pool_id: The user pool ID
        :param provider_name: The identity provider name
        :return:
        """
        self.client.update_identity_provider(
            UserPoolId=pool_id,
            ProviderName=provider_name,
            **kwargs,
        )

    def describe_user_pool_client(self, pool_id: str, client_id: str):
        """
        Returns configuration information of a specified user pool app client
        :param pool_id: The user pool ID
        :param client_id: The client ID
        :return: client json
        """
        return self.client.describe_user_pool_client(
            UserPoolId=pool_id, ClientId=client_id
        )["UserPoolClient"]

    def admin_update_user_pool_client(self, pool_id: str, client_id: str, **kwargs):
        """
        Updates configuration information of a specified user pool app client
        :param pool_id: The identity pool ID
        :param client_id: The identity pool name
        :return:
        """
        self.client.update_user_pool_client(
            UserPoolId=pool_id,
            ClientId=client_id,
            **kwargs,
        )

    def associate_software_token(self):
        """
        Get the Secret code used for Software Token MFA.
        :return: Secret code
        :rtype: string
        """
        response = self.client.associate_software_token(AccessToken=self.access_token)
        return response["SecretCode"]

    def verify_software_token(self, code, device_name=""):
        """
        Verify the value generated by TOTP to complete the registration of Software Token MFA.
        :param code: The value generated by TOTP
        :param device_name: Device name to register (optional)
        :return: verify success
        :rtype: bool
        """
        response = self.client.verify_software_token(
            AccessToken=self.access_token, UserCode=code, FriendlyDeviceName=device_name
        )
        return response["Status"] == "SUCCESS"

    def set_user_mfa_preference(self, sms_mfa, software_token_mfa, preferred=None):
        """
        Register the preference of MFA.
        :param sms_mfa: Enable SMS MFA.
        :type sms_mfa: bool
        :param software_token_mfa: Enable Software Token MFA.
        :type software_token_mfa: bool
        :param preferred: "SMS" or "SOFTWARE_TOKEN", or None if both of the previous arguments are False.
        :type preferred: string
        :return:
        """
        sms_mfa_settings = {"Enabled": bool(sms_mfa), "PreferredMfa": False}
        software_token_mfa_settings = {
            "Enabled": bool(software_token_mfa),
            "PreferredMfa": False,
        }
        if not (bool(sms_mfa) or bool(software_token_mfa)):
            # Disable MFA
            pass
        elif preferred == "SMS":
            sms_mfa_settings["PreferredMfa"] = True
        elif preferred == "SOFTWARE_TOKEN":
            software_token_mfa_settings["PreferredMfa"] = True
        else:
            raise ValueError(
                "preferred must have a value of 'SMS', 'SOFTWARE_TOKEN', or None."
            )
        self.client.set_user_mfa_preference(
            SMSMfaSettings=sms_mfa_settings,
            SoftwareTokenMfaSettings=software_token_mfa_settings,
            AccessToken=self.access_token,
        )

    def respond_to_software_token_mfa_challenge(self, code, mfa_tokens=None):
        """
        Response to software token MFA challenge.
        :param code: software token MFA code.
        :type code: string
        :param mfa_token: Token stored in MFAChallengeException. Optional if you have not regenerated the Cognito instance.
        :type mfa_token: string
        :return:
        """
        if not mfa_tokens:
            mfa_tokens = self.mfa_tokens
        challenge_responses = {
            "USERNAME": self.username,
            "SOFTWARE_TOKEN_MFA_CODE": str(code),
        }
        self._add_secret_hash(challenge_responses, "SECRET_HASH")
        tokens = self.client.respond_to_auth_challenge(
            ClientId=self.client_id,
            Session=mfa_tokens["Session"],
            ChallengeName="SOFTWARE_TOKEN_MFA",
            ChallengeResponses=challenge_responses,
        )
        self._set_tokens(tokens)

    def respond_to_sms_mfa_challenge(self, code, mfa_tokens=None):
        """
        Response to SMS MFA challenge.
        :param code: SMS MFA code.
        :type code: string
        :param mfa_tokens: Token stored in MFAChallengeException. Optional if you have not regenerated the Cognito instance.
        :type mfa_tokens: string
        :return:
        """
        if not mfa_tokens:
            mfa_tokens = self.mfa_tokens
        challenge_responses = {
            "USERNAME": self.username,
            "SMS_MFA_CODE": code,
        }
        self._add_secret_hash(challenge_responses, "SECRET_HASH")
        tokens = self.client.respond_to_auth_challenge(
            ClientId=self.client_id,
            Session=mfa_tokens["Session"],
            ChallengeName="SMS_MFA",
            ChallengeResponses=challenge_responses,
        )
        self._set_tokens(tokens)
