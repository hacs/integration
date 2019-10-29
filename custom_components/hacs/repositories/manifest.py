"""
Manifest handling of a repository.

https://hacs.xyz/docs/publish/start#hacsjson
"""
from typing import List
import attr

from custom_components.hacs.hacsbase.exceptions import HacsRepositoryInfo


@attr.s(auto_attribs=True)
class HacsManifest:
    """HacsManifest class."""

    name: str = ""
    content_in_root: bool = False
    zip_release: bool = False
    filename: str = None
    manifest: dict = {}
    hacs: str = ""
    domains: List[str] = []
    country: List[str] = []
    homeassistant: str = None
    persistent_directory: str = None
    iot_class: str = None
    render_readme: bool = False

    @staticmethod
    def from_dict(manifest: dict):
        """Set attributes from dicts."""
        if manifest is None:
            raise HacsRepositoryInfo("Missing manifest data")

        manifest_data = HacsManifest()

        manifest_data.manifest = manifest

        for key in manifest:
            setattr(manifest_data, key, manifest[key])
        return manifest_data
