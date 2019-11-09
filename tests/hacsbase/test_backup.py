"""HACS Backup Test Suite."""
# pylint: disable=missing-docstring
import os
from custom_components.hacs.hacsbase.backup import Backup


def test_file(tmpdir):
    with open(f"{tmpdir.dirname}/dummy_file", "w") as dummy:
        dummy.write("")

    backup = Backup(f"{tmpdir.dirname}/dummy_file")
    backup.create()

    assert not os.path.exists(backup.local_path)
    assert os.path.exists(backup.backup_path_full)

    backup.restore()
    assert os.path.exists(backup.local_path)

    backup.cleanup()
    assert not os.path.exists(backup.backup_path_full)


def test_directory(tmpdir):
    os.makedirs(f"{tmpdir.dirname}/dummy_directory", exist_ok=True)

    backup = Backup(f"{tmpdir.dirname}/dummy_directory")
    backup.create()

    assert not os.path.exists(backup.local_path)
    assert os.path.exists(backup.backup_path_full)

    backup.restore()
    assert os.path.exists(backup.local_path)

    backup.cleanup()
    assert not os.path.exists(backup.backup_path_full)


def test_muilti(tmpdir):
    backup = Backup(f"{tmpdir.dirname}/dummy_directory")
    backup.create()
    backup.create()
