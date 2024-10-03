"""
Utils to fetch CHIP Development Product Attestation Authority (PAA) certificates from DCL.

This is based on the original script from project-chip here:
https://github.com/project-chip/connectedhomeip/edit/master/credentials/fetch-paa-certs-from-dcl.py

All rights reserved.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import logging
from pathlib import Path
import re
import warnings

from aiohttp import ClientError, ClientSession
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.utils import CryptographyDeprecationWarning

from matter_server.server.helpers import DCL_PRODUCTION_URL, DCL_TEST_URL

# Git repo details
OWNER = "project-chip"
REPO = "connectedhomeip"
PATH = "credentials/development/paa-root-certs"

LOGGER = logging.getLogger(__name__)
GIT_URL = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/master/{PATH}"


# Subject Key Identifier of certificates. The Subject Key Identifier is a mandatory
# X.509 extensions for Matter uniquely identifying the public key of PAA certificates.
CERT_SUBJECT_KEY_IDS: set[str] = set()


async def write_paa_root_cert(
    paa_root_cert_dir: Path, base_name: str, pem_certificate: str, subject: str
) -> bool:
    """Write certificate from string to file."""

    def _write(
        paa_root_cert_dir: Path,
        filename_base: str,
        pem_certificate: str,
        der_certificate: bytes,
    ) -> None:
        # handle PEM certificate file
        file_path_pem = paa_root_cert_dir.joinpath(f"{filename_base}.pem")
        LOGGER.debug("Writing PEM certificate %s", file_path_pem)
        file_path_pem.write_text(pem_certificate)
        # handle DER certificate file (converted from PEM)
        file_path_der = paa_root_cert_dir.joinpath(f"{filename_base}.der")
        LOGGER.debug("Writing DER certificate %s", file_path_der)
        file_path_der.write_bytes(der_certificate)

    filename_base = base_name + re.sub(
        "[^a-zA-Z0-9_-]", "", re.sub("[=, ]", "_", subject)
    )

    # Some certificates lead to a warning from the cryptography library:
    # CryptographyDeprecationWarning: The parsed certificate contains a
    # NULL parameter value in its signature algorithm parameters.
    with warnings.catch_warnings():
        if LOGGER.isEnabledFor(logging.DEBUG):
            # Use always so warnings are printed for each offending cert.
            warnings.simplefilter("always", CryptographyDeprecationWarning)
        else:
            # Ignore the warnings generally. The problem has been reported to the CSA
            # via Slack.
            warnings.simplefilter("ignore", CryptographyDeprecationWarning)

        cert = x509.load_pem_x509_certificate(pem_certificate.encode())

    ski: x509.SubjectKeyIdentifier = cert.extensions.get_extension_for_class(
        x509.SubjectKeyIdentifier
    ).value
    ski_formatted = ":".join(f"{byte:02X}" for byte in ski.digest)
    if ski_formatted in CERT_SUBJECT_KEY_IDS:
        LOGGER.debug(
            "Skipping '%s', certificate with the same subject key identifier already stored.",
            subject,
        )
        return False
    CERT_SUBJECT_KEY_IDS.add(ski_formatted)

    der_certificate = cert.public_bytes(serialization.Encoding.DER)

    await asyncio.get_running_loop().run_in_executor(
        None,
        _write,
        paa_root_cert_dir,
        f"{filename_base}_{ski.digest.hex()}",
        pem_certificate,
        der_certificate,
    )

    return True


async def fetch_dcl_certificates(
    paa_root_cert_dir: Path,
    base_name: str,
    base_url: str,
) -> int:
    """Fetch DCL PAA Certificates."""
    fetch_count: int = 0

    try:
        async with ClientSession(raise_for_status=True) as http_session:
            # fetch the paa certificates list
            async with http_session.get(
                f"{base_url}/dcl/pki/root-certificates"
            ) as response:
                result = await response.json()
            paa_list = result["approvedRootCertificates"]["certs"]
            # grab each certificate
            for paa in paa_list:
                # do not fetch a certificate if we already fetched it
                if paa["subjectKeyId"] in CERT_SUBJECT_KEY_IDS:
                    continue
                url = f"{base_url}/dcl/pki/certificates/{paa['subject']}/{paa['subjectKeyId']}"
                LOGGER.debug("Downloading certificate from %s", url)
                async with http_session.get(url) as response:
                    result = await response.json()

                certificate_data: dict = result["approvedCertificates"]["certs"][0]
                certificate: str = certificate_data["pemCert"]
                subject = certificate_data["subjectAsText"]
                certificate = certificate.rstrip("\n")
                if await write_paa_root_cert(
                    paa_root_cert_dir,
                    base_name,
                    certificate,
                    subject,
                ):
                    fetch_count += 1
    except (ClientError, TimeoutError) as err:
        LOGGER.warning(
            "Fetching latest certificates failed: error %s", err, exc_info=err
        )

    return fetch_count


# Manufacturers release test certificates through the SDK (Git) as a part
# of their standard product release workflow. This will ensure those certs
# are correctly captured


async def fetch_git_certificates(
    paa_root_cert_dir: Path, prefix: str | None = None
) -> int:
    """Fetch Git PAA Certificates."""
    fetch_count = 0
    LOGGER.info("Fetching the latest PAA root certificates from Git.")

    try:
        async with ClientSession(raise_for_status=True) as http_session:
            # Fetch directory contents and filter out extension
            api_url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{PATH}"
            async with http_session.get(api_url) as response:
                contents = await response.json()
                git_certs = {item["name"].split(".")[0] for item in contents}
            # Fetch certificates
            for cert in git_certs:
                if prefix and not cert.startswith(prefix):
                    continue
                async with http_session.get(f"{GIT_URL}/{cert}.pem") as response:
                    certificate = await response.text()
                if await write_paa_root_cert(
                    paa_root_cert_dir, "git_", certificate, cert
                ):
                    fetch_count += 1
    except (ClientError, TimeoutError) as err:
        LOGGER.warning(
            "Fetching latest certificates failed: error %s", err, exc_info=err
        )

    LOGGER.info("Fetched %s PAA root certificates from Git.", fetch_count)

    return fetch_count


async def fetch_certificates(
    paa_root_cert_dir: Path,
    fetch_test_certificates: bool = True,
    fetch_production_certificates: bool = True,
) -> int:
    """Fetch PAA Certificates."""
    loop = asyncio.get_running_loop()
    paa_root_cert_dir_version = paa_root_cert_dir / ".version"

    def _check_paa_root_dir(
        paa_root_cert_dir: Path, paa_root_cert_dir_version: Path
    ) -> datetime | None:
        """Return timestamp of last fetch or None if a initial download is required."""
        if paa_root_cert_dir.is_dir():
            if paa_root_cert_dir_version.exists():
                stat = paa_root_cert_dir_version.stat()
                return datetime.fromtimestamp(stat.st_mtime, tz=UTC)

            # Old certificate store version, delete all files
            LOGGER.info("Old PAA root certificate store found, removing certificates.")
            for path in paa_root_cert_dir.iterdir():
                if not path.is_dir():
                    path.unlink()
        else:
            paa_root_cert_dir.mkdir(parents=True)
        return None

    last_fetch = await loop.run_in_executor(
        None, _check_paa_root_dir, paa_root_cert_dir, paa_root_cert_dir_version
    )
    if last_fetch and last_fetch > datetime.now(tz=UTC) - timedelta(days=1):
        LOGGER.info("Skip fetching certificates (already fetched within the last 24h).")
        return 0

    total_fetch_count = 0

    LOGGER.info("Fetching the latest PAA root certificates from DCL.")

    # Determine which url's need to be queried.
    if fetch_production_certificates:
        fetch_count = await fetch_dcl_certificates(
            paa_root_cert_dir=paa_root_cert_dir,
            base_name="dcld_production_",
            base_url=DCL_PRODUCTION_URL,
        )
        LOGGER.info("Fetched %s PAA root certificates from DCL.", fetch_count)
        total_fetch_count += fetch_count

    if fetch_test_certificates:
        fetch_count = await fetch_dcl_certificates(
            paa_root_cert_dir=paa_root_cert_dir,
            base_name="dcld_test_",
            base_url=DCL_TEST_URL,
        )
        LOGGER.info("Fetched %s PAA root certificates from Test DCL.", fetch_count)
        total_fetch_count += fetch_count

    if fetch_test_certificates:
        total_fetch_count += await fetch_git_certificates(paa_root_cert_dir)
    else:
        # Treat the Chip-Test certificates as production, we use them in our examples
        total_fetch_count += await fetch_git_certificates(
            paa_root_cert_dir, "Chip-Test"
        )

    await loop.run_in_executor(None, paa_root_cert_dir_version.write_text, "1")

    return fetch_count
