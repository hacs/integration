"""Tarfile fileobject handler for encrypted files."""

import hashlib
import logging
import os
import tarfile
import time
from contextlib import contextmanager
from pathlib import Path, PurePath
from typing import IO, BinaryIO, Generator, Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import (
    Cipher,
    CipherContext,
    algorithms,
    modes,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)

BLOCK_SIZE = 16
BLOCK_SIZE_BITS = 128
DEFAULT_BUFSIZE = 10240

MOD_READ = "r"
MOD_WRITE = "w"


class SecureTarFile:
    """Handle encrypted files for tarfile library."""

    def __init__(
        self,
        name: Path,
        mode: str,
        key: Optional[bytes] = None,
        gzip: bool = True,
        bufsize: int = DEFAULT_BUFSIZE,
        fileobj: Optional[IO[bytes]] = None,
    ) -> None:
        """Initialize encryption handler."""
        self._file: Optional[IO[bytes]] = None
        self._mode: str = mode
        self._name: Path = name
        self._bufsize: int = bufsize
        self._extra_args = {}
        self._fileobj = fileobj

        # Tarfile options
        self._tar: Optional[tarfile.TarFile] = None
        if key:
            self._tar_mode = f"{mode}|"
        else:
            self._tar_mode = f"{mode}:"
            if gzip:
                self._extra_args["compresslevel"] = 6

        if gzip:
            self._tar_mode = self._tar_mode + "gz"

        # Encryption/Description
        self._aes: Optional[Cipher] = None
        self._key: Optional[bytes] = key

        # Function helper
        self._decrypt: Optional[CipherContext] = None
        self._encrypt: Optional[CipherContext] = None

    def create_inner_tar(
        self, name: str, key: Optional[bytes] = None, gzip: bool = True
    ) -> "_InnerSecureTarFile":
        """Create inner tar file."""
        return _InnerSecureTarFile(
            self._tar,
            name=Path(name),
            mode=self._mode,
            key=key,
            gzip=gzip,
            bufsize=self._bufsize,
        )

    def __enter__(self) -> tarfile.TarFile:
        """Start context manager tarfile."""
        if not self._key:
            self._tar = tarfile.open(
                name=str(self._name),
                mode=self._tar_mode,
                dereference=False,
                bufsize=self._bufsize,
                **self._extra_args,
                **({"fileobj": self._fileobj} if self._fileobj else {}),
            )
            return self._tar

        # Encrypted/Decrypted Tarfile

        if self._fileobj:
            # If we have a fileobj, we don't need to open a file
            self._file = self._fileobj
        else:
            read_mode = self._mode.startswith("r")
            if read_mode:
                file_mode: int = os.O_RDONLY
            else:
                file_mode = os.O_WRONLY | os.O_CREAT

            fd = os.open(self._name, file_mode, 0o666)
            self._file = os.fdopen(fd, "rb" if read_mode else "wb")

        # Extract IV for CBC
        if self._mode == MOD_READ:
            cbc_rand = self._file.read(16)
        else:
            cbc_rand = os.urandom(16)
            self._file.write(cbc_rand)

        # Create Cipher
        self._aes = Cipher(
            algorithms.AES(self._key),
            modes.CBC(_generate_iv(self._key, cbc_rand)),
            backend=default_backend(),
        )

        self._decrypt = self._aes.decryptor()
        self._encrypt = self._aes.encryptor()

        self._tar = tarfile.open(
            fileobj=self,
            mode=self._tar_mode,
            dereference=False,
            bufsize=self._bufsize,
        )
        return self._tar

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Close file."""
        if self._tar:
            self._tar.close()
            self._tar = None
        if self._file:
            if not self._fileobj:
                self._file.close()
            self._file = None

    def write(self, data: bytes) -> None:
        """Write data."""
        if len(data) % BLOCK_SIZE != 0:
            padder = padding.PKCS7(BLOCK_SIZE_BITS).padder()
            data = padder.update(data) + padder.finalize()

        self._file.write(self._encrypt.update(data))

    def read(self, size: int = 0) -> bytes:
        """Read data."""
        return self._decrypt.update(self._file.read(size))

    @property
    def path(self) -> Path:
        """Return path object of tarfile."""
        return self._name

    @property
    def size(self) -> float:
        """Return backup size."""
        if not self._name.is_file():
            return 0
        return round(self._name.stat().st_size / 1_048_576, 2)  # calc mbyte


class _InnerSecureTarFile(SecureTarFile):
    """Handle encrypted files for tarfile library inside another tarfile."""

    def __init__(
        self,
        outer_tar: tarfile.TarFile,
        name: Path,
        mode: str,
        key: Optional[bytes] = None,
        gzip: bool = True,
        bufsize: int = DEFAULT_BUFSIZE,
    ) -> None:
        """Initialize inner handler."""
        super().__init__(
            name=name,
            mode=mode,
            key=key,
            gzip=gzip,
            bufsize=bufsize,
            fileobj=outer_tar.fileobj,
        )
        self.outer_tar = outer_tar
        self.stream: Generator[BinaryIO, None, None] | None = None

    def __enter__(self) -> tarfile.TarFile:
        """Start context manager tarfile."""
        tar_info = tarfile.TarInfo(name=str(self._name))
        if self.outer_tar.format == tarfile.PAX_FORMAT:
            # Ensure we always set mtime as a float to force
            # a PAX header to be written.
            #
            # This is necessary to
            # handle large files as TarInfo.tobuf will try to
            # use a shorter ustar header if we do not have at
            # least one float in the tarinfo.
            # https://github.com/python/cpython/blob/53b84e772cac6e4a55cebf908d6bb9c48fe254dc/Lib/tarfile.py#L1066
            tar_info.mtime = time.time()
        else:
            tar_info.mtime = int(time.time())
        self.stream = _add_stream(self.outer_tar, tar_info)
        self.stream.__enter__()
        return super().__enter__()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Close file."""
        super().__exit__(exc_type, exc_value, traceback)
        self.stream.__exit__(exc_type, exc_value, traceback)


@contextmanager
def _add_stream(
    tar: tarfile.TarFile, tar_info: tarfile.TarInfo
) -> Generator[BinaryIO, None, None]:
    """Add a stream to the tarfile.

    This only works with uncompressed, unencrypted tar files.

    The typical usage is:

    with _add_stream(tar, tar_info) as fileobj:
        fileobj.write(data)

    It is critical that the tar_info is not modified
    inside the context manager, as the tar file header
    size may change.
    """
    fileobj = tar.fileobj
    tell_before_adding_inner_file_header = fileobj.tell()
    # Write an empty header for the inner tar file
    # We'll seek back to this position later to update the header with the correct size
    tar_info_header = tar_info.tobuf(tar.format, tar.encoding, tar.errors)
    tar_info_header_len = len(tar_info_header)
    fileobj.write(tar_info_header)
    try:
        yield fileobj
    finally:
        tell_after_writing_inner_tar = fileobj.tell()
        size_of_inner_tar = (
            tell_after_writing_inner_tar
            - tell_before_adding_inner_file_header
            - tar_info_header_len
        )
        # Pad the outer tar file to a multiple of BLOCKSIZE
        # in case the inner tar file is not a multiple of BLOCKSIZE
        blocks, remainder = divmod(size_of_inner_tar, tarfile.BLOCKSIZE)
        padding_size = 0
        if remainder > 0:
            padding_size = tarfile.BLOCKSIZE - remainder
            fileobj.write(tarfile.NUL * padding_size)
            blocks += 1
        tar.offset += size_of_inner_tar + padding_size

        tar_info.size = size_of_inner_tar
        # Now that we know the size of the inner tar, we seek back
        # to where we started and re-add the member with the correct size
        fileobj.seek(tell_before_adding_inner_file_header)
        tar.addfile(tar_info)
        # Finally return to the end of the outer tar file
        fileobj.seek(tell_after_writing_inner_tar + padding_size)


def _generate_iv(key: bytes, salt: bytes) -> bytes:
    """Generate an iv from data."""
    temp_iv = key + salt
    for _ in range(100):
        temp_iv = hashlib.sha256(temp_iv).digest()
    return temp_iv[:16]


def secure_path(tar: tarfile.TarFile) -> Generator[tarfile.TarInfo, None, None]:
    """Security safe check of path.
    Prevent ../ or absolut paths
    """
    for member in tar:
        file_path = Path(member.name)
        try:
            if file_path.is_absolute():
                raise ValueError()
            Path("/fake", file_path).resolve().relative_to("/fake")
        except (ValueError, RuntimeError):
            _LOGGER.warning("Found issue with file %s", file_path)
            continue
        else:
            yield member


def _is_excluded_by_filter(path: PurePath, exclude_list: list[str]) -> bool:
    """Filter to filter excludes."""

    for exclude in exclude_list:
        if not path.match(exclude):
            continue
        _LOGGER.debug("Ignoring %s because of %s", path, exclude)
        return True

    return False


def atomic_contents_add(
    tar_file: tarfile.TarFile,
    origin_path: Path,
    excludes: list[str],
    arcname: str = ".",
) -> None:
    """Append directories and/or files to the TarFile if excludes wont filter."""

    if _is_excluded_by_filter(origin_path, excludes):
        return None

    # Add directory only (recursive=False) to ensure we also archive empty directories
    tar_file.add(origin_path.as_posix(), arcname=arcname, recursive=False)

    for directory_item in origin_path.iterdir():
        if _is_excluded_by_filter(directory_item, excludes):
            continue

        arcpath = PurePath(arcname, directory_item.name).as_posix()
        if directory_item.is_dir() and not directory_item.is_symlink():
            atomic_contents_add(tar_file, directory_item, excludes, arcpath)
            continue

        tar_file.add(directory_item.as_posix(), arcname=arcpath, recursive=False)

    return None
