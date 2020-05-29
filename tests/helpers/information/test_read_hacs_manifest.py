"""Helpers: Information: read_hacs_manifest."""
# pylint: disable=missing-docstring
import os
import json
from custom_components.hacs.globals import get_hacs
from custom_components.hacs.helpers.information import read_hacs_manifest


def temp_cleanup(tmpdir):
    hacsdir = f"{tmpdir.dirname}/custom_components/hacs"
    manifestfile = f"{hacsdir}/manifest.json"
    if os.path.exists(manifestfile):
        os.remove(manifestfile)
    if os.path.exists(hacsdir):
        os.removedirs(hacsdir)


def test_read_hacs_manifest(tmpdir):
    hacsdir = f"{tmpdir.dirname}/custom_components/hacs"
    manifestfile = f"{hacsdir}/manifest.json"
    hacs = get_hacs()
    hacs.system.config_path = tmpdir.dirname

    data = {"test": "test"}

    os.makedirs(hacsdir, exist_ok=True)
    with open(manifestfile, "w") as manifest_file:
        manifest_file.write(json.dumps(data))

    manifest = read_hacs_manifest()
    assert data == manifest
    temp_cleanup(tmpdir)
