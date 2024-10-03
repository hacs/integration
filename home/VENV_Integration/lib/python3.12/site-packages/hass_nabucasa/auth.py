"""Package to communicate with the authentication API."""

from __future__ import annotations

import asyncio
from functools import lru_cache, partial
import logging
import random
from typing import TYPE_CHECKING, Any

import async_timeout
import boto3
import botocore
from botocore.exceptions import BotoCoreError, ClientError
import pycognito
from pycognito.exceptions import ForceChangePasswordException

from .const import MESSAGE_AUTH_FAIL

if TYPE_CHECKING:
    from . import Cloud, _ClientT

_LOGGER = logging.getLogger(__name__)


class CloudError(Exception):
    """Base class for cloud related errors."""


class Unauthenticated(CloudError):
    """Raised when authentication failed."""


class UserNotFound(CloudError):
    """Raised when a user is not found."""


class UserExists(CloudError):
    """Raised when a username already exists."""


class UserNotConfirmed(CloudError):
    """Raised when a user has not confirmed email yet."""


class PasswordChangeRequired(CloudError):
    """Raised when a password change is required."""

    # https://github.com/PyCQA/pylint/issues/1085
    # pylint: disable=useless-super-delegation
    def __init__(self, message: str = "Password change required.") -> None:
        """Initialize a password change required error."""
        super().__init__(message)


class UnknownError(CloudError):
    """Raised when an unknown error occurs."""


AWS_EXCEPTIONS: dict[str, type[CloudError]] = {
    "UserNotFoundException": UserNotFound,
    "UserNotConfirmedException": UserNotConfirmed,
    "UsernameExistsException": UserExists,
    "NotAuthorizedException": Unauthenticated,
    "PasswordResetRequiredException": PasswordChangeRequired,
}


class CognitoAuth:
    """Handle cloud auth."""

    def __init__(self, cloud: Cloud[_ClientT]) -> None:
        """Configure the auth api."""
        self.cloud = cloud
        self._refresh_task: asyncio.Task | None = None
        self._session: boto3.Session | None = None
        self._request_lock = asyncio.Lock()

        cloud.iot.register_on_connect(self.on_connect)
        cloud.iot.register_on_disconnect(self.on_disconnect)

    async def _async_handle_token_refresh(self) -> None:
        """Handle Cloud access token refresh."""
        sleep_time = random.randint(2400, 3600)
        while True:
            try:
                await asyncio.sleep(sleep_time)
                await self.async_renew_access_token()
            except CloudError as err:
                _LOGGER.error("Can't refresh cloud token: %s", err)
            except asyncio.CancelledError:
                # Task is canceled, stop it.
                break

            sleep_time = random.randint(3100, 3600)

    async def on_connect(self) -> None:
        """When the instance is connected."""
        self._refresh_task = asyncio.create_task(self._async_handle_token_refresh())

    async def on_disconnect(self) -> None:
        """When the instance is disconnected."""
        if self._refresh_task is not None:
            self._refresh_task.cancel()

    async def async_register(
        self,
        email: str,
        password: str,
        *,
        client_metadata: Any | None = None,
    ) -> None:
        """Register a new account."""
        try:
            async with self._request_lock:
                cognito = await self.cloud.run_executor(
                    self._create_cognito_client,
                )
                await self.cloud.run_executor(
                    partial(
                        cognito.register,
                        email,
                        password,
                        client_metadata=client_metadata,
                    ),
                )

        except ClientError as err:
            raise _map_aws_exception(err) from err
        except BotoCoreError as err:
            raise UnknownError from err

    async def async_resend_email_confirm(self, email: str) -> None:
        """Resend email confirmation."""
        try:
            async with self._request_lock:
                cognito = await self.cloud.run_executor(
                    partial(self._create_cognito_client, username=email),
                )
                await self.cloud.run_executor(
                    partial(
                        cognito.client.resend_confirmation_code,
                        Username=email,
                        ClientId=cognito.client_id,
                    ),
                )
        except ClientError as err:
            raise _map_aws_exception(err) from err
        except BotoCoreError as err:
            raise UnknownError from err

    async def async_forgot_password(self, email: str) -> None:
        """Initialize forgotten password flow."""
        try:
            async with self._request_lock:
                cognito = await self.cloud.run_executor(
                    partial(self._create_cognito_client, username=email),
                )
                await self.cloud.run_executor(cognito.initiate_forgot_password)

        except ClientError as err:
            raise _map_aws_exception(err) from err
        except BotoCoreError as err:
            raise UnknownError from err

    async def async_login(self, email: str, password: str) -> None:
        """Log user in and fetch certificate."""
        try:
            async with self._request_lock:
                assert not self.cloud.is_logged_in, "Cannot login if already logged in."

                cognito = await self.cloud.run_executor(
                    partial(self._create_cognito_client, username=email),
                )

                async with async_timeout.timeout(30):
                    await self.cloud.run_executor(
                        partial(cognito.authenticate, password=password),
                    )

                task = await self.cloud.update_token(
                    cognito.id_token,
                    cognito.access_token,
                    cognito.refresh_token,
                )

            if task:
                await task

        except ForceChangePasswordException as err:
            raise PasswordChangeRequired from err

        except ClientError as err:
            raise _map_aws_exception(err) from err

        except BotoCoreError as err:
            raise UnknownError from err

    async def async_check_token(self) -> None:
        """Check that the token is valid and renew if necessary."""
        async with self._request_lock:
            cognito = await self._async_authenticated_cognito()
            if not cognito.check_token(renew=False):
                return

            try:
                await self._async_renew_access_token()
            except (Unauthenticated, UserNotFound) as err:
                _LOGGER.error("Unable to refresh token: %s", err)

                self.cloud.client.user_message(
                    "cloud_subscription_expired",
                    "Home Assistant Cloud",
                    MESSAGE_AUTH_FAIL,
                )

                # Don't await it because it could cancel this task
                asyncio.create_task(self.cloud.logout())
                raise

    async def async_renew_access_token(self) -> None:
        """Renew access token."""
        async with self._request_lock:
            await self._async_renew_access_token()

    async def _async_renew_access_token(self) -> None:
        """Renew access token internals.

        Does not consume lock.
        """
        cognito = await self._async_authenticated_cognito()

        try:
            await self.cloud.run_executor(cognito.renew_access_token)
            await self.cloud.update_token(cognito.id_token, cognito.access_token)

        except ClientError as err:
            raise _map_aws_exception(err) from err

        except BotoCoreError as err:
            raise UnknownError from err

    async def _async_authenticated_cognito(self) -> pycognito.Cognito:
        """Return an authenticated cognito instance."""
        if self.cloud.access_token is None or self.cloud.refresh_token is None:
            raise Unauthenticated("No authentication found")

        return await self.cloud.run_executor(
            partial(
                self._create_cognito_client,
                access_token=self.cloud.access_token,
                refresh_token=self.cloud.refresh_token,
            ),
        )

    def _create_cognito_client(self, **kwargs: Any) -> pycognito.Cognito:
        """Create a new cognito client.

        NOTE: This will do I/O
        """
        if self._session is None:
            self._session = boto3.session.Session()

        return _cached_cognito(
            user_pool_id=self.cloud.user_pool_id,
            client_id=self.cloud.cognito_client_id,
            user_pool_region=self.cloud.region,
            botocore_config=botocore.config.Config(signature_version=botocore.UNSIGNED),
            session=self._session,
            **kwargs,
        )


def _map_aws_exception(err: ClientError) -> CloudError:
    """Map AWS exception to our exceptions."""
    ex = AWS_EXCEPTIONS.get(err.response["Error"]["Code"], UnknownError)
    return ex(err.response["Error"]["Message"])


@lru_cache(maxsize=2)
def _cached_cognito(
    user_pool_id: str,
    client_id: str,
    user_pool_region: str,
    botocore_config: Any,
    session: Any,
    **kwargs: Any,
) -> pycognito.Cognito:
    """Create a cached cognito client.

    NOTE: This will do I/O
    """
    return pycognito.Cognito(
        user_pool_id=user_pool_id,
        client_id=client_id,
        user_pool_region=user_pool_region,
        botocore_config=botocore_config,
        session=session,
        **kwargs,
    )
