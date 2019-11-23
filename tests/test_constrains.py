"""HACS Constrains Test Suite."""
# pylint: disable=missing-docstring,invalid-name
import json
import os
from custom_components.hacs.constrains import (
    constrain_translations,
    constrain_custom_updater,
    constrain_version,
    check_constans,
)
from custom_components.hacs.hacsbase import Hacs

HAVERSION = "9.99.9"


def temp_cleanup(tmpdir):
    manifest = f"{tmpdir.dirname}/custom_components/hacs/manifest.json"
    translations_dir = f"{tmpdir.dirname}/custom_components/hacs/.translations"
    custom_updater1 = f"{tmpdir.dirname}/custom_components/custom_updater/__init__.py"
    custom_updater2 = f"{tmpdir.dirname}/custom_components/custom_updater.py"

    if os.path.exists(manifest):
        os.remove(manifest)
    if os.path.exists(translations_dir):
        os.removedirs(translations_dir)
    if os.path.exists(custom_updater1):
        os.remove(custom_updater1)
    if os.path.exists(custom_updater2):
        os.remove(custom_updater2)


def test_check_constans(tmpdir):
    hacs = Hacs()
    hacs.system.ha_version = HAVERSION
    hacs.system.config_path = tmpdir.dirname

    assert not check_constans(hacs)

    translations_dir = f"{hacs.system.config_path}/custom_components/hacs/.translations"
    os.makedirs(translations_dir, exist_ok=True)

    manifest_dir = f"{hacs.system.config_path}/custom_components/hacs"
    os.makedirs(manifest_dir, exist_ok=True)
    with open(f"{manifest_dir}/manifest.json", "w") as manifest:
        manifest.write(json.dumps({"homeassistant": "9.99.8"}))
    assert constrain_version(hacs)

    assert check_constans(hacs)

    temp_cleanup(tmpdir)


def test_ha_version(tmpdir):
    hacs = Hacs()
    hacs.system.ha_version = HAVERSION
    hacs.system.config_path = tmpdir.dirname

    manifest_dir = f"{hacs.system.config_path}/custom_components/hacs"
    os.makedirs(manifest_dir, exist_ok=True)

    with open(f"{manifest_dir}/manifest.json", "w") as manifest:
        manifest.write(json.dumps({"homeassistant": HAVERSION}))
    assert constrain_version(hacs)

    with open(f"{manifest_dir}/manifest.json", "w") as manifest:
        manifest.write(json.dumps({"homeassistant": "9.99.8"}))
    assert constrain_version(hacs)

    with open(f"{manifest_dir}/manifest.json", "w") as manifest:
        manifest.write(json.dumps({"homeassistant": "10.0.0"}))
    assert not constrain_version(hacs)

    temp_cleanup(tmpdir)


def test_custom_updater(tmpdir):
    hacs = Hacs()
    hacs.system.config_path = tmpdir.dirname

    assert constrain_custom_updater(hacs)

    custom_updater_dir = f"{hacs.system.config_path}/custom_components/custom_updater"
    os.makedirs(custom_updater_dir, exist_ok=True)
    with open(f"{custom_updater_dir}/__init__.py", "w") as cufile:
        cufile.write("")
    assert not constrain_custom_updater(hacs)

    custom_updater_dir = f"{hacs.system.config_path}/custom_components"
    os.makedirs(custom_updater_dir, exist_ok=True)
    with open(f"{custom_updater_dir}/custom_updater.py", "w") as cufile:
        cufile.write("")
    assert not constrain_custom_updater(hacs)

    temp_cleanup(tmpdir)


def test_translations(tmpdir):
    hacs = Hacs()
    hacs.system.config_path = tmpdir.dirname

    assert not constrain_translations(hacs)

    translations_dir = f"{hacs.system.config_path}/custom_components/hacs/.translations"
    os.makedirs(translations_dir, exist_ok=True)
    assert constrain_translations(hacs)

    temp_cleanup(tmpdir)
