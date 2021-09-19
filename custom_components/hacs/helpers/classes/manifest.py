"""
Manifest handling of a repository.

https://hacs.xyz/docs/publish/start#hacsjson
"""
from typing import List

import attr

from custom_components.hacs.exceptions import HacsException

MANIFEST_DATA_KEYS = {
    "name",
    "content_in_root",
    "zip_release",
    "filename",
    "manifest",
    "hacs",
    "hide_default_branch",
    "domains",
    "country",
    "homeassistant",
    "persistent_directory",
    "iot_class",
    "render_readme",
    "description",
    "version",
    "codeowners",
    "documentation",
    "issue_tracker",
    "config_flow",
    "domain",
}


@attr.s(slots=True)
class HacsManifest:
    """HacsManifest class."""

    name: str = attr.ib(default=None)
    content_in_root: bool = attr.ib(default=False)
    zip_release: bool = attr.ib(default=False)
    filename: str = attr.ib(default=None)
    manifest: dict = attr.ib(default={})
    hacs: str = attr.ib(default=None)
    hide_default_branch: bool = attr.ib(default=False)
    domains: List[str] = attr.ib(default=[])
    country: List[str] = attr.ib(default=[])
    homeassistant: str = attr.ib(default=None)
    persistent_directory: str = attr.ib(default=None)
    iot_class: str = attr.ib(default=None)
    render_readme: bool = attr.ib(default=False)
    description: str = attr.ib(default=None)
    version: str = attr.ib(default=None)
    codeowners: List[str] = attr.ib(default=[])
    documentation: str = attr.ib(default=None)
    issue_tracker: str = attr.ib(default=None)
    config_flow: bool = attr.ib(default=False)
    domain: str = attr.ib(default=None)

    @staticmethod
    def from_dict(manifest: dict):
        """Set attributes from dicts."""
        if manifest is None:
            raise HacsException("Missing manifest data")

        manifest_data = HacsManifest(
            **{k: v for k, v in manifest.items() if k in MANIFEST_DATA_KEYS}
        )

        manifest_data.manifest = manifest

        if country := manifest.get("country"):
            if isinstance(country, str):
                manifest["country"] = [country]

        return manifest_data
