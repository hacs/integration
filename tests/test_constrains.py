"""HACS Constrains Test Suite."""
# pylint: disable=missing-docstring,invalid-name
import os

from custom_components.hacs.helpers.functions.constrains import (
    check_constrains,
    constrain_custom_updater,
    constrain_version,
)
from custom_components.hacs.share import get_hacs

HAVERSION = "9.99.9"


def temp_cleanup(tmpdir):
    manifest = f"{tmpdir.dirname}/custom_components/hacs/manifest.json"
    custom_updater1 = f"{tmpdir.dirname}/custom_components/custom_updater/__init__.py"
    custom_updater2 = f"{tmpdir.dirname}/custom_components/custom_updater.py"

    if os.path.exists(manifest):
        os.remove(manifest)
    if os.path.exists(custom_updater1):
        os.remove(custom_updater1)
    if os.path.exists(custom_updater2):
        os.remove(custom_updater2)


def test_check_constrains(tmpdir):
    hacs = get_hacs()
    hacs.system.ha_version = HAVERSION
    hacs.system.config_path = tmpdir.dirname

    assert check_constrains()

    custom_updater_dir = f"{hacs.system.config_path}/custom_components/custom_updater"
    os.makedirs(custom_updater_dir, exist_ok=True)
    with open(f"{custom_updater_dir}/__init__.py", "w") as cufile:
        cufile.write("")

    assert not check_constrains()
    temp_cleanup(tmpdir)

    hacs.system.ha_version = "0.97.0"
    assert not check_constrains()

    hacs.system.ha_version = HAVERSION

    assert constrain_version()
    assert check_constrains()

    temp_cleanup(tmpdir)


def test_ha_version(tmpdir):
    hacs = get_hacs()
    hacs.system.config_path = tmpdir.dirname

    hacs.system.ha_version = HAVERSION
    assert constrain_version()

    hacs.system.ha_version = "1.0.0"
    assert constrain_version()

    hacs.system.ha_version = "0.97.0"
    assert not constrain_version()

    temp_cleanup(tmpdir)


def test_custom_updater(tmpdir):
    hacs = get_hacs()
    hacs.system.config_path = tmpdir.dirname

    assert constrain_custom_updater()

    custom_updater_dir = f"{hacs.system.config_path}/custom_components/custom_updater"
    os.makedirs(custom_updater_dir, exist_ok=True)
    with open(f"{custom_updater_dir}/__init__.py", "w") as cufile:
        cufile.write("")
    assert not constrain_custom_updater()

    custom_updater_dir = f"{hacs.system.config_path}/custom_components"
    os.makedirs(custom_updater_dir, exist_ok=True)
    with open(f"{custom_updater_dir}/custom_updater.py", "w") as cufile:
        cufile.write("")
    assert not constrain_custom_updater()

    temp_cleanup(tmpdir)
