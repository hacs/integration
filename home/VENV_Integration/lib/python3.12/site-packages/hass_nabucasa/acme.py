"""Handle ACME and local certificates."""

from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import TYPE_CHECKING
import urllib

from acme import challenges, client, crypto_util, errors, messages
import async_timeout
from atomicwrites import atomic_write
import attr
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.extensions import SubjectAlternativeName
from cryptography.x509.oid import NameOID
import josepy as jose
import OpenSSL

from . import cloud_api
from .utils import utcnow

FILE_ACCOUNT_KEY = "acme_account.pem"
FILE_PRIVATE_KEY = "remote_private.pem"
FILE_FULLCHAIN = "remote_fullchain.pem"
FILE_REGISTRATION = "acme_reg.json"

ACCOUNT_KEY_SIZE = 2048
PRIVATE_KEY_SIZE = 2048
USER_AGENT = "home-assistant-cloud"

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from . import Cloud, _ClientT


class AcmeClientError(Exception):
    """Raise if a acme client error raise."""


class AcmeChallengeError(AcmeClientError):
    """Raise if a challenge fails."""


class AcmeJWSVerificationError(AcmeClientError):
    """Raise if a JWS verification fails."""


class AcmeNabuCasaError(AcmeClientError):
    """Raise errors on nabucasa API."""


@attr.s
class ChallengeHandler:
    """Handle ACME data over a challenge."""

    challenge = attr.ib(type=messages.ChallengeBody)
    order = attr.ib(type=messages.OrderResource)
    response = attr.ib(type=challenges.ChallengeResponse)
    validation = attr.ib(type=str)


class AcmeHandler:
    """Class handle a local certification."""

    def __init__(self, cloud: Cloud[_ClientT], domains: list[str], email: str) -> None:
        """Initialize local ACME Handler."""
        self.cloud = cloud
        self._acme_server = f"https://{cloud.acme_server}/directory"
        self._account_jwk: jose.JWKRSA | None = None
        self._acme_client: client.ClientV2 | None = None
        self._x509: x509.Certificate | None = None

        self._domains = domains
        self._email = email

    @property
    def email(self) -> str:
        """Return the email."""
        return self._email

    @property
    def domains(self) -> list[str]:
        """Return the domains."""
        return self._domains

    @property
    def path_account_key(self) -> Path:
        """Return path of account key."""
        return Path(self.cloud.path(FILE_ACCOUNT_KEY))

    @property
    def path_private_key(self) -> Path:
        """Return path of private key."""
        return Path(self.cloud.path(FILE_PRIVATE_KEY))

    @property
    def path_fullchain(self) -> Path:
        """Return path of cert fullchain."""
        return Path(self.cloud.path(FILE_FULLCHAIN))

    @property
    def path_registration_info(self) -> Path:
        """Return path of acme client registration file."""
        return Path(self.cloud.path(FILE_REGISTRATION))

    @property
    def certificate_available(self) -> bool:
        """Return True if a certificate is loaded."""
        return self._x509 is not None

    @property
    def is_valid_certificate(self) -> bool:
        """Validate date of a certificate and return True is valid."""
        if (expire_date := self.expire_date) is None:
            return False
        return expire_date > utcnow()

    @property
    def expire_date(self) -> datetime | None:
        """Return datetime of expire date for certificate."""
        if not self._x509:
            return None
        return self._x509.not_valid_after_utc

    @property
    def common_name(self) -> str | None:
        """Return CommonName of certificate."""
        if not self._x509:
            return None
        return str(
            self._x509.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value,
        )

    @property
    def alternative_names(self) -> list[str] | None:
        """Return alternative names of certificate."""
        if not self._x509:
            return None

        alternative_names = self._x509.extensions.get_extension_for_class(
            SubjectAlternativeName,
        ).value
        return [str(entry.value) for entry in alternative_names]

    @property
    def fingerprint(self) -> str | None:
        """Return SHA1 hex string as fingerprint."""
        if not self._x509:
            return None
        fingerprint = self._x509.fingerprint(hashes.SHA1())
        return fingerprint.hex()

    def _generate_csr(self) -> bytes:
        """Load or create private key."""
        if self.path_private_key.exists():
            _LOGGER.debug("Load private keyfile: %s", self.path_private_key)
            key_pem = self.path_private_key.read_bytes()
        else:
            _LOGGER.debug("create private keyfile: %s", self.path_private_key)
            key = OpenSSL.crypto.PKey()
            key.generate_key(OpenSSL.crypto.TYPE_RSA, PRIVATE_KEY_SIZE)
            key_pem = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key)

            self.path_private_key.write_bytes(key_pem)
            self.path_private_key.chmod(0o600)

        return crypto_util.make_csr(key_pem, self._domains)

    def _load_account_key(self) -> None:
        """Load or create account key."""
        if self.path_account_key.exists():
            _LOGGER.debug("Load account keyfile: %s", self.path_account_key)
            pem = self.path_account_key.read_bytes()
            key = serialization.load_pem_private_key(pem, password=None)

        else:
            _LOGGER.debug("Create new RSA keyfile: %s", self.path_account_key)
            key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=ACCOUNT_KEY_SIZE,
            )

            # Store it to file
            pem = key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            self.path_account_key.write_bytes(pem)
            self.path_account_key.chmod(0o600)

        if TYPE_CHECKING:
            assert isinstance(key, rsa.RSAPrivateKey)
        self._account_jwk = jose.JWKRSA(key=jose.ComparableRSAKey(key))

    def _create_client(self) -> None:
        """Create new ACME client."""
        if self.path_registration_info.exists():
            _LOGGER.info("Load exists ACME registration")
            regr = messages.RegistrationResource.json_loads(
                self.path_registration_info.read_text(encoding="utf-8"),
            )

            acme_url = urllib.parse.urlparse(self._acme_server)
            regr_url = urllib.parse.urlparse(regr.uri)

            if acme_url[0] != regr_url[0] or acme_url[1] != regr_url[1]:
                _LOGGER.info("Reset new ACME registration")
                self.path_registration_info.unlink()
                self.path_account_key.unlink()

        # Make sure that account key is loaded
        self._load_account_key()
        assert self._account_jwk is not None

        # Load a exists registration
        if self.path_registration_info.exists():
            try:
                network = client.ClientNetwork(
                    self._account_jwk,
                    account=regr,
                    user_agent=USER_AGENT,
                )
                directory = client.ClientV2.get_directory(
                    url=self._acme_server,
                    net=network,
                )
                self._acme_client = client.ClientV2(directory=directory, net=network)
            except (errors.Error, ValueError) as err:
                # https://github.com/certbot/certbot/blob/63fb97d8dea73ba63964f69fac0b15acfed02b3e/acme/acme/client.py#L670
                # The client raises ValueError for RequestException
                raise AcmeClientError(f"Can't connect to ACME server: {err}") from err
            return

        # Create a new registration
        try:
            network = client.ClientNetwork(self._account_jwk, user_agent=USER_AGENT)
            directory = client.ClientV2.get_directory(
                url=self._acme_server,
                net=network,
            )
            self._acme_client = client.ClientV2(directory=directory, net=network)
        except (errors.Error, ValueError) as err:
            raise AcmeClientError(f"Can't connect to ACME server: {err}") from err

        try:
            _LOGGER.info(
                "Register a ACME account with TOS: %s",
                self._acme_client.directory.meta.terms_of_service,
            )
            regr = self._acme_client.new_account(
                messages.NewRegistration.from_data(
                    email=self._email,
                    terms_of_service_agreed=True,
                ),
            )
        except errors.Error as err:
            raise AcmeClientError(f"Can't register to ACME server: {err}") from err

        # Store registration info
        self.path_registration_info.write_text(
            regr.json_dumps_pretty(),
            encoding="utf-8",
        )
        self.path_registration_info.chmod(0o600)

    def _create_order(self, csr_pem: bytes) -> messages.OrderResource:
        """Initialize domain challenge and return token."""
        _LOGGER.info("Initialize challenge for a new ACME certificate")
        assert self._acme_client is not None
        try:
            return self._acme_client.new_order(csr_pem)
        except (messages.Error, errors.Error) as err:
            if (
                isinstance(err, messages.Error)
                and err.typ == "urn:ietf:params:acme:error:malformed"
                and err.detail == "JWS verification error"
            ):
                raise AcmeJWSVerificationError(
                    f"JWS verification failed: {err}",
                ) from None
            raise AcmeChallengeError(
                f"Can't order a new ACME challenge: {err}",
            ) from None

    def _start_challenge(self, order: messages.OrderResource) -> list[ChallengeHandler]:
        """Initialize domain challenge and return token."""
        _LOGGER.info("Start challenge for a new ACME certificate")

        # Find DNS challenge
        # pylint: disable=not-an-iterable
        dns_challenges: list[messages.ChallengeBody] = []
        for auth in order.authorizations:
            for challenge in auth.body.challenges:
                if challenge.typ != "dns-01":
                    continue
                dns_challenges.append(challenge)

        if len(dns_challenges) == 0:
            raise AcmeChallengeError("No pending ACME challenge")

        handlers = []

        for dns_challenge in dns_challenges:
            try:
                response, validation = dns_challenge.response_and_validation(
                    self._account_jwk,
                )
            except errors.Error as err:
                raise AcmeChallengeError(
                    f"Can't validate the new ACME challenge: {err}",
                ) from None
            handlers.append(
                ChallengeHandler(dns_challenge, order, response, validation),
            )

        return handlers

    def _answer_challenge(self, handler: ChallengeHandler) -> None:
        """Answer challenge."""
        _LOGGER.info("Answer challenge for the new ACME certificate")
        if TYPE_CHECKING:
            assert self._acme_client is not None
        try:
            self._acme_client.answer_challenge(handler.challenge, handler.response)
        except errors.Error as err:
            raise AcmeChallengeError(f"Can't accept ACME challenge: {err}") from err

    def _finish_challenge(self, order: messages.OrderResource) -> None:
        """Wait until challenge is finished."""
        # Wait until it's authorize and fetch certification
        if TYPE_CHECKING:
            assert self._acme_client is not None
        deadline = datetime.now() + timedelta(seconds=90)
        try:
            order = self._acme_client.poll_authorizations(order, deadline)
            order = self._acme_client.finalize_order(
                order,
                deadline,
                fetch_alternative_chains=True,
            )
        except errors.Error as err:
            raise AcmeChallengeError(f"Wait of ACME challenge fails: {err}") from err
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception while finalizing order")
            raise AcmeChallengeError(
                "Unexpected exception while finalizing order",
            ) from None

        # Cleanup the old stuff
        if self.path_fullchain.exists():
            _LOGGER.info("Renew old certificate: %s", self.path_fullchain)
            self.path_fullchain.unlink()
        else:
            _LOGGER.info("Create new certificate: %s", self.path_fullchain)

        with atomic_write(self.path_fullchain, overwrite=True) as fp:
            fp.write(order.fullchain_pem)
        self.path_fullchain.chmod(0o600)

    async def load_certificate(self) -> None:
        """Get x509 Cert-Object."""
        if self._x509 or not self.path_fullchain.exists():
            return

        def _load_cert() -> x509.Certificate:
            """Load certificate in a thread."""
            return x509.load_pem_x509_certificate(self.path_fullchain.read_bytes())

        try:
            self._x509 = await self.cloud.run_executor(_load_cert)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception loading certificate")

    def _revoke_certificate(self) -> None:
        """Revoke certificate."""
        if not self.path_fullchain.exists():
            _LOGGER.warning("Can't revoke not exists certificate")
            return

        if self._acme_client is None:
            _LOGGER.error("No acme client")
            return

        fullchain = jose.ComparableX509(
            OpenSSL.crypto.load_certificate(
                OpenSSL.crypto.FILETYPE_PEM,
                self.path_fullchain.read_bytes(),
            ),
        )

        _LOGGER.info("Revoke certificate")
        try:
            # https://letsencrypt.org/docs/revoking/#specifying-a-reason-code
            self._acme_client.revoke(fullchain, 4)
        except errors.ConflictError:
            pass
        except errors.Error as err:
            # Ignore errors where certificate did not exist
            if "No such certificate" in str(err):  # noqa: SIM114
                pass
            # Ignore errors where certificate has expired
            elif "Certificate is expired" in str(err):  # noqa: SIM114
                pass
            # Ignore errors where unrecognized issuer (happens dev/prod switch)
            elif "Certificate from unrecognized issuer" in str(err):
                pass
            else:
                raise AcmeClientError(f"Can't revoke certificate: {err}") from err

    def _deactivate_account(self) -> None:
        """Deactivate account."""
        if not self.path_registration_info.exists() or self._acme_client is None:
            return

        _LOGGER.info("Load exists ACME registration")
        regr = messages.RegistrationResource.json_loads(
            self.path_registration_info.read_text(encoding="utf-8"),
        )

        try:
            self._acme_client.deactivate_registration(regr)
        except errors.Error as err:
            raise AcmeClientError(f"Can't deactivate account: {err}") from err

    def _have_any_file(self) -> bool:
        return (
            self.path_registration_info.exists()
            or self.path_account_key.exists()
            or self.path_fullchain.exists()
            or self.path_private_key.exists()
        )

    def _remove_files(self) -> None:
        self.path_registration_info.unlink(missing_ok=True)
        self.path_account_key.unlink(missing_ok=True)
        self.path_fullchain.unlink(missing_ok=True)
        self.path_private_key.unlink(missing_ok=True)

    async def issue_certificate(self) -> None:
        """Create/Update certificate."""
        if not self._acme_client:
            await self.cloud.run_executor(self._create_client)

        # Initialize challenge / new certificate
        csr = await self.cloud.run_executor(self._generate_csr)
        order = await self.cloud.run_executor(self._create_order, csr)
        dns_challenges: list[ChallengeHandler] = await self.cloud.run_executor(
            self._start_challenge,
            order,
        )

        try:
            for challenge in dns_challenges:
                # Update DNS
                try:
                    async with async_timeout.timeout(30):
                        resp = await cloud_api.async_remote_challenge_txt(
                            self.cloud,
                            challenge.validation,
                        )
                    assert resp.status in (200, 201)
                except (TimeoutError, AssertionError):
                    raise AcmeNabuCasaError(
                        "Can't set challenge token to NabuCasa DNS!",
                    ) from None

                # Answer challenge
                try:
                    _LOGGER.info(
                        "Waiting 60 seconds for publishing DNS to ACME provider",
                    )
                    await asyncio.sleep(60)
                    await self.cloud.run_executor(self._answer_challenge, challenge)
                except AcmeChallengeError as err:
                    _LOGGER.error("Could not complete answer challenge - %s", err)
                    # There is no point in continuing here
                    break
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception while answering challenge")
                    # There is no point in continuing here
                    break
        finally:
            try:
                async with async_timeout.timeout(30):
                    # We only need to cleanup for the last entry
                    await cloud_api.async_remote_challenge_cleanup(
                        self.cloud,
                        dns_challenges[-1].validation,
                    )
            except TimeoutError:
                _LOGGER.error("Failed to clean up challenge from NabuCasa DNS!")

        # Finish validation
        try:
            await self.cloud.run_executor(self._finish_challenge, order)
        except AcmeChallengeError as err:
            raise AcmeNabuCasaError(f"Could not finish challenge - {err}") from err
        await self.load_certificate()

    async def reset_acme(self) -> None:
        """Revoke and deactivate acme certificate/account."""
        _LOGGER.info("Revoke and deactivate ACME user/certificate")
        if (
            self._acme_client is None
            and self._account_jwk is None
            and self._x509 is None
            and not await self.cloud.run_executor(self._have_any_file)
        ):
            _LOGGER.info("ACME user/certificates already cleaned up")
            return

        if not self._acme_client:
            await self.cloud.run_executor(self._create_client)

        try:
            with contextlib.suppress(AcmeClientError):
                await self.cloud.run_executor(self._revoke_certificate)
            with contextlib.suppress(AcmeClientError):
                await self.cloud.run_executor(self._deactivate_account)
        finally:
            self._acme_client = None
            self._account_jwk = None
            self._x509 = None
            await self.cloud.run_executor(self._remove_files)

    async def hardening_files(self) -> None:
        """Control permission on files."""

        def _control() -> None:
            # Set file permission to 0600
            if self.path_account_key.exists():
                self.path_account_key.chmod(0o600)
            if self.path_registration_info.exists():
                self.path_registration_info.chmod(0o600)
            if self.path_fullchain.exists():
                self.path_fullchain.chmod(0o600)
            if self.path_private_key.exists():
                self.path_private_key.chmod(0o600)

        try:
            await self.cloud.run_executor(_control)
        except OSError:
            _LOGGER.warning("Can't check and hardening file permission")
