import base64
import binascii
import datetime
import hashlib
import hmac
import json
import os
import re
import platform
import requests

import boto3

from .exceptions import (
    ForceChangePasswordException,
    SoftwareTokenMFAChallengeException,
    SMSMFAChallengeException,
)

# https://github.com/aws/amazon-cognito-identity-js/blob/master/src/AuthenticationHelper.js#L22
N_HEX = (
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
    "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
    "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
    "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
    "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
    "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
    "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
    "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
    "15728E5A8AAAC42DAD33170D04507A33A85521ABDF1CBA64"
    "ECFB850458DBEF0A8AEA71575D060C7DB3970F85A6E1E4C7"
    "ABF5AE8CDB0933D71E8C94E04A25619DCEE3D2261AD2EE6B"
    "F12FFA06D98A0864D87602733EC86A64521F2B18177B200C"
    "BBE117577A615D6C770988C0BAD946E208E24FA074E5AB31"
    "43DB5BFCE0FD108E4B82D120A93AD2CAFFFFFFFFFFFFFFFF"
)
# https://github.com/aws/amazon-cognito-identity-js/blob/master/src/AuthenticationHelper.js#L49
G_HEX = "2"
INFO_BITS = bytearray("Caldera Derived Key", "utf-8")
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTH_NAMES = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


def hash_sha256(buf):
    """AuthenticationHelper.hash"""
    value = hashlib.sha256(buf).hexdigest()
    return (64 - len(value)) * "0" + value


def hex_hash(hex_string):
    return hash_sha256(bytearray.fromhex(hex_string))


def hex_to_long(hex_string):
    return int(hex_string, 16)


def long_to_hex(long_num):
    return f"{long_num:x}"


def get_random(nbytes):
    random_hex = binascii.hexlify(os.urandom(nbytes))
    return hex_to_long(random_hex)


def pad_hex(long_int):
    """
    Converts a Long integer (or hex string) to hex format padded with zeroes for hashing
    :param {Long integer|String} long_int Number or string to pad.
    :return {String} Padded hex string.
    """
    if not isinstance(long_int, str):
        hash_str = long_to_hex(long_int)
    else:
        hash_str = long_int
    if len(hash_str) % 2 == 1:
        hash_str = f"0{hash_str}"
    elif hash_str[0] in "89ABCDEFabcdef":
        hash_str = f"00{hash_str}"
    return hash_str


def compute_hkdf(ikm, salt):
    """
    Standard hkdf algorithm
    :param {Buffer} ikm Input key material.
    :param {Buffer} salt Salt value.
    :return {Buffer} Strong key material.
    @private
    """
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    info_bits_update = INFO_BITS + bytearray(chr(1), "utf-8")
    hmac_hash = hmac.new(prk, info_bits_update, hashlib.sha256).digest()
    return hmac_hash[:16]


def calculate_u(big_a, big_b):
    """
    Calculate the client's value U which is the hash of A and B
    :param {Long integer} big_a Large A value.
    :param {Long integer} big_b Server B value.
    :return {Long integer} Computed U value.
    """
    u_hex_hash = hex_hash(pad_hex(big_a) + pad_hex(big_b))
    return hex_to_long(u_hex_hash)


def generate_hash_device(device_group_key, device_key):
    # source: https://github.com/amazon-archives/amazon-cognito-identity-js/blob/6b87f1a30a998072b4d98facb49dcaf8780d15b0/src/AuthenticationHelper.js#L137

    # random device password, which will be used for DEVICE_SRP_AUTH flow
    device_password = base64.standard_b64encode(os.urandom(40)).decode("utf-8")

    combined_string = f"{device_group_key}{device_key}:{device_password}"
    combined_string_hash = hash_sha256(combined_string.encode("utf-8"))
    salt = pad_hex(get_random(16))

    x_value = hex_to_long(hex_hash(salt + combined_string_hash))
    g_value = hex_to_long(G_HEX)
    big_n = hex_to_long(N_HEX)
    verifier_device_not_padded = pow(g_value, x_value, big_n)
    verifier = pad_hex(verifier_device_not_padded)

    device_secret_verifier_config = {
        "PasswordVerifier": base64.standard_b64encode(
            bytearray.fromhex(verifier)
        ).decode("utf-8"),
        "Salt": base64.standard_b64encode(bytearray.fromhex(salt)).decode("utf-8"),
    }
    return device_password, device_secret_verifier_config


class AWSSRP:

    SMS_MFA_CHALLENGE = "SMS_MFA"
    SOFTWARE_TOKEN_MFA_CHALLENGE = "SOFTWARE_TOKEN_MFA"
    NEW_PASSWORD_REQUIRED_CHALLENGE = "NEW_PASSWORD_REQUIRED"
    PASSWORD_VERIFIER_CHALLENGE = "PASSWORD_VERIFIER"
    DEVICE_SRP_CHALLENGE = "DEVICE_SRP_AUTH"
    DEVICE_PASSWORD_VERIFIER_CHALLENGE = "DEVICE_PASSWORD_VERIFIER"

    def __init__(
        self,
        username,
        password,
        pool_id,
        client_id,
        pool_region=None,
        client=None,
        client_secret=None,
        device_key=None,
        device_group_key=None,
        device_password=None,
    ):
        if pool_region is not None and client is not None:
            raise ValueError(
                "pool_region and client should not both be specified "
                "(region should be passed to the boto3 client instead)"
            )
        if (
            device_key is not None
            or device_group_key is not None
            or device_password is not None
        ):
            if (
                device_key is None
                or device_group_key is None
                or device_password is None
            ):
                raise ValueError(
                    "Either all device_key, device_group_key, and device_password should be specified or none at all "
                )

        self.username = username
        self.password = password
        self.pool_id = pool_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.client = (
            client if client else boto3.client("cognito-idp", region_name=pool_region)
        )
        self.device_key = device_key
        self.device_group_key = device_group_key
        self.device_password = device_password
        self.big_n = hex_to_long(N_HEX)
        self.val_g = hex_to_long(G_HEX)
        self.val_k = hex_to_long(hex_hash("00" + N_HEX + "0" + G_HEX))
        self.small_a_value = self.generate_random_small_a()
        self.large_a_value = self.calculate_a()
        self.access_token = None
        self.device_name = None
        self.cognito_idp_url = None

    def generate_random_small_a(self):
        """
        helper function to generate a random big integer
        :return {Long integer} a random value.
        """
        random_long_int = get_random(128)
        return random_long_int % self.big_n

    def calculate_a(self):
        """
        Calculate the client's public value A = g^a%N
        with the generated random number a
        :param {Long integer} a Randomly generated small A.
        :return {Long integer} Computed large A.
        """
        big_a = pow(self.val_g, self.small_a_value, self.big_n)
        # safety check
        if (big_a % self.big_n) == 0:
            raise ValueError("Safety check for A failed")
        return big_a

    def get_password_authentication_key(self, username, password, server_b_value, salt):
        """
        Calculates the final hkdf based on computed S value, and computed U value and the key
        :param {String} username Username.
        :param {String} password Password.
        :param {Long integer} server_b_value Server B value.
        :param {Long integer} salt Generated salt.
        :return {Buffer} Computed HKDF value.
        """
        u_value = calculate_u(self.large_a_value, server_b_value)
        if u_value == 0:
            raise ValueError("U cannot be zero.")
        username_password = f"{self.pool_id.split('_')[1]}{username}:{password}"
        username_password_hash = hash_sha256(username_password.encode("utf-8"))

        x_value = hex_to_long(hex_hash(pad_hex(salt) + username_password_hash))
        g_mod_pow_xn = pow(self.val_g, x_value, self.big_n)
        int_value2 = server_b_value - self.val_k * g_mod_pow_xn
        s_value = pow(int_value2, self.small_a_value + u_value * x_value, self.big_n)
        hkdf = compute_hkdf(
            bytearray.fromhex(pad_hex(s_value)),
            bytearray.fromhex(pad_hex(long_to_hex(u_value))),
        )
        return hkdf

    def get_device_authentication_key(
        self, device_group_key, device_key, device_password, server_b_value, salt
    ):
        u_value = calculate_u(self.large_a_value, server_b_value)
        if u_value == 0:
            raise ValueError("U cannot be zero.")
        username_password = f"{device_group_key}{device_key}:{device_password}"
        username_password_hash = hash_sha256(username_password.encode("utf-8"))

        x_value = hex_to_long(hex_hash(pad_hex(salt) + username_password_hash))
        g_mod_pow_xn = pow(self.val_g, x_value, self.big_n)
        int_value2 = server_b_value - self.val_k * g_mod_pow_xn
        s_value = pow(int_value2, self.small_a_value + u_value * x_value, self.big_n)
        hkdf = compute_hkdf(
            bytearray.fromhex(pad_hex(s_value)),
            bytearray.fromhex(pad_hex(long_to_hex(u_value))),
        )
        return hkdf

    def get_auth_params(self):
        auth_params = {
            "USERNAME": self.username,
            "SRP_A": long_to_hex(self.large_a_value),
        }
        if self.client_secret is not None:
            auth_params.update(
                {
                    "SECRET_HASH": self.get_secret_hash(
                        self.username, self.client_id, self.client_secret
                    )
                }
            )
        if self.device_key is not None:
            auth_params.update({"DEVICE_KEY": self.device_key})
        return auth_params

    @staticmethod
    def get_secret_hash(username, client_id, client_secret):
        message = bytearray(username + client_id, "utf-8")
        hmac_obj = hmac.new(bytearray(client_secret, "utf-8"), message, hashlib.sha256)
        return base64.standard_b64encode(hmac_obj.digest()).decode("utf-8")

    @staticmethod
    def get_cognito_formatted_timestamp(input_datetime):
        return f"{WEEKDAY_NAMES[input_datetime.weekday()]} {MONTH_NAMES[input_datetime.month - 1]} {input_datetime.day:d} {input_datetime.hour:02d}:{input_datetime.minute:02d}:{input_datetime.second:02d} UTC {input_datetime.year:d}"

    def process_challenge(self, challenge_parameters, request_parameters):
        internal_username = challenge_parameters.get(
            "USERNAME", request_parameters["USERNAME"]
        )
        user_id_for_srp = challenge_parameters["USER_ID_FOR_SRP"]
        salt_hex = challenge_parameters["SALT"]
        srp_b_hex = challenge_parameters["SRP_B"]
        secret_block_b64 = challenge_parameters["SECRET_BLOCK"]
        timestamp = self.get_cognito_formatted_timestamp(datetime.datetime.utcnow())
        hkdf = self.get_password_authentication_key(
            user_id_for_srp, self.password, hex_to_long(srp_b_hex), salt_hex
        )
        secret_block_bytes = base64.standard_b64decode(secret_block_b64)
        msg = (
            bytearray(self.pool_id.split("_")[1], "utf-8")
            + bytearray(user_id_for_srp, "utf-8")
            + bytearray(secret_block_bytes)
            + bytearray(timestamp, "utf-8")
        )

        hmac_obj = hmac.new(hkdf, msg, digestmod=hashlib.sha256)
        signature_string = base64.standard_b64encode(hmac_obj.digest())
        response = {
            "TIMESTAMP": timestamp,
            "USERNAME": internal_username,
            "PASSWORD_CLAIM_SECRET_BLOCK": secret_block_b64,
            "PASSWORD_CLAIM_SIGNATURE": signature_string.decode("utf-8"),
        }
        if self.client_secret is not None:
            response.update(
                {
                    "SECRET_HASH": self.get_secret_hash(
                        internal_username, self.client_id, self.client_secret
                    )
                }
            )
        if self.device_key is not None:
            response.update({"DEVICE_KEY": self.device_key})
        return response

    def process_device_challenge(self, challenge_parameters):
        username = challenge_parameters["USERNAME"]
        salt_hex = challenge_parameters["SALT"]
        srp_b_hex = challenge_parameters["SRP_B"]
        secret_block_b64 = challenge_parameters["SECRET_BLOCK"]
        # re strips leading zero from a day number (required by AWS Cognito)
        timestamp = re.sub(
            r" 0(\d) ",
            r" \1 ",
            datetime.datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y"),
        )
        hkdf = self.get_device_authentication_key(
            self.device_group_key,
            self.device_key,
            self.device_password,
            hex_to_long(srp_b_hex),
            salt_hex,
        )
        secret_block_bytes = base64.standard_b64decode(secret_block_b64)
        msg = (
            bytearray(self.device_group_key, "utf-8")
            + bytearray(self.device_key, "utf-8")
            + bytearray(secret_block_bytes)
            + bytearray(timestamp, "utf-8")
        )
        hmac_obj = hmac.new(hkdf, msg, digestmod=hashlib.sha256)
        signature_string = base64.standard_b64encode(hmac_obj.digest())
        response = {
            "TIMESTAMP": timestamp,
            "USERNAME": username,
            "PASSWORD_CLAIM_SECRET_BLOCK": secret_block_b64,
            "PASSWORD_CLAIM_SIGNATURE": signature_string.decode("utf-8"),
            "DEVICE_KEY": self.device_key,
        }
        if self.client_secret is not None:
            response.update(
                {
                    "SECRET_HASH": self.get_secret_hash(
                        username, self.client_id, self.client_secret
                    )
                }
            )
        return response

    def authenticate_user(self, client=None, client_metadata=None):
        boto_client = self.client or client
        auth_params = self.get_auth_params()
        response = boto_client.initiate_auth(
            AuthFlow="USER_SRP_AUTH",
            AuthParameters=auth_params,
            ClientId=self.client_id,
        )
        if response["ChallengeName"] == self.PASSWORD_VERIFIER_CHALLENGE:
            challenge_response = self.process_challenge(
                response["ChallengeParameters"], auth_params
            )
            tokens = boto_client.respond_to_auth_challenge(
                ClientId=self.client_id,
                ChallengeName=self.PASSWORD_VERIFIER_CHALLENGE,
                ChallengeResponses=challenge_response,
                **({"ClientMetadata": client_metadata} if client_metadata else {}),
            )
            if tokens.get("ChallengeName") == self.DEVICE_SRP_CHALLENGE:
                challenge_response = {
                    "USERNAME": self.username,
                    "DEVICE_KEY": self.device_key,
                    "SRP_A": long_to_hex(self.large_a_value),
                }
                response = boto_client.respond_to_auth_challenge(
                    ClientId=self.client_id,
                    ChallengeName="DEVICE_SRP_AUTH",
                    ChallengeResponses=challenge_response,
                )
                challenge_response = self.process_device_challenge(
                    response["ChallengeParameters"]
                )
                tokens = boto_client.respond_to_auth_challenge(
                    ClientId=self.client_id,
                    ChallengeName="DEVICE_PASSWORD_VERIFIER",
                    ChallengeResponses=challenge_response,
                )
                return tokens

            if tokens.get("ChallengeName") == self.NEW_PASSWORD_REQUIRED_CHALLENGE:
                raise ForceChangePasswordException(
                    "Change password before authenticating"
                )

            if tokens.get("ChallengeName") == self.SMS_MFA_CHALLENGE:
                raise SMSMFAChallengeException("Do SMS MFA", tokens)

            if tokens.get("ChallengeName") == self.SOFTWARE_TOKEN_MFA_CHALLENGE:
                raise SoftwareTokenMFAChallengeException(
                    "Do Software Token MFA", tokens
                )

            return tokens

        raise NotImplementedError(
            f"The {response['ChallengeName']} challenge is not supported"
        )

    def set_new_password_challenge(self, new_password, client=None):
        boto_client = self.client or client
        auth_params = self.get_auth_params()
        response = boto_client.initiate_auth(
            AuthFlow="USER_SRP_AUTH",
            AuthParameters=auth_params,
            ClientId=self.client_id,
        )
        if response["ChallengeName"] == self.PASSWORD_VERIFIER_CHALLENGE:
            challenge_response = self.process_challenge(
                response["ChallengeParameters"], auth_params
            )
            tokens = boto_client.respond_to_auth_challenge(
                ClientId=self.client_id,
                ChallengeName=self.PASSWORD_VERIFIER_CHALLENGE,
                ChallengeResponses=challenge_response,
            )

            if tokens["ChallengeName"] == self.NEW_PASSWORD_REQUIRED_CHALLENGE:
                challenge_parameters = response["ChallengeParameters"]
                challenge_response.update(
                    {
                        "USERNAME": challenge_parameters["USERNAME"],
                        "NEW_PASSWORD": new_password,
                    }
                )
                new_password_response = boto_client.respond_to_auth_challenge(
                    ClientId=self.client_id,
                    ChallengeName=self.NEW_PASSWORD_REQUIRED_CHALLENGE,
                    Session=tokens["Session"],
                    ChallengeResponses=challenge_response,
                )
                return new_password_response
            return tokens

        raise NotImplementedError(
            f"The {response['ChallengeName']} challenge is not supported"
        )

    def confirm_device(self, tokens, device_name=None):
        self.access_token = tokens["AuthenticationResult"]["AccessToken"]
        self.device_key = tokens["AuthenticationResult"]["NewDeviceMetadata"][
            "DeviceKey"
        ]
        self.device_group_key = tokens["AuthenticationResult"]["NewDeviceMetadata"][
            "DeviceGroupKey"
        ]
        self.device_name = device_name
        self.cognito_idp_url = (
            f"https://cognito-idp.{self.pool_id.split('_')[0]}.amazonaws.com/"
        )
        device_password, device_secret_verifier_config = generate_hash_device(
            self.device_group_key, self.device_key
        )
        if device_name is None:
            device_name = platform.node()
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityProviderService.ConfirmDevice",
        }
        data = {
            "AccessToken": self.access_token,
            "DeviceKey": self.device_key,
            "DeviceName": device_name,
            "DeviceSecretVerifierConfig": device_secret_verifier_config,
        }
        response = requests.post(
            self.cognito_idp_url, headers=headers, data=json.dumps(data), timeout=30
        )
        return response, device_password

    def update_device_status(self, is_remembered, access_token, device_key):
        self.cognito_idp_url = (
            f"https://cognito-idp.{self.pool_id.split('_')[0]}.amazonaws.com/"
        )
        self.access_token = access_token
        self.device_key = device_key
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityProviderService.UpdateDeviceStatus",
        }
        if is_remembered is True:
            status = "remembered"
        elif is_remembered is False:
            status = "not_remembered"
        data = {
            "AccessToken": self.access_token,
            "DeviceKey": self.device_key,
            "DeviceRememberedStatus": status,
        }
        response = requests.post(
            self.cognito_idp_url, headers=headers, data=json.dumps(data), timeout=30
        )
        return f"{response} : {response.json}"

    def forget_device(self, access_token, device_key):
        self.cognito_idp_url = (
            f"https://cognito-idp.{self.pool_id.split('_')[0]}.amazonaws.com/"
        )
        self.access_token = access_token
        self.device_key = device_key
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityProviderService.ForgetDevice",
        }
        data = {"AccessToken": self.access_token, "DeviceKey": self.device_key}
        response = requests.post(
            self.cognito_idp_url, headers=headers, data=json.dumps(data), timeout=30
        )
        return f"{response} : {response.json}"
