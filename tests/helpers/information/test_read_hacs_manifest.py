"""Helpers: Information: read_hacs_manifest."""
import json

# pylint: disable=missing-docstring
import os

from custom_components.hacs.utils.information import read_hacs_manifest


def temp_cleanup(tmpdir):
    hacsdir = f"{tmpdir.dirname}/custom_components/hacs"
    manifestfile = f"{hacsdir}/manifest.json"
    if os.path.exists(manifestfile):
        os.remove(manifestfile)
    if os.path.exists(hacsdir):
        os.removedirs(hacsdir)


def test_read_hacs_manifest(hacs, tmpdir):
    hacsdir = f"{tmpdir.dirname}/custom_components/hacs"
    manifestfile = f"{hacsdir}/manifest.json"
    hacs.core.config_path = tmpdir.dirname

    data = {"test": "test"}

    os.makedirs(hacsdir, exist_ok=True)
    with open(manifestfile, "w") as manifest_file:
        manifest_file.write(json.dumps(data))

    manifest = read_hacs_manifest()
    assert data == manifest
    temp_cleanup(tmpdir)
