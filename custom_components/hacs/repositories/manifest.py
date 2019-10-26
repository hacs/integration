"""
Manifest handling of a repository.

https://hacs.xyz/docs/publish/start#hacsjson
"""
from typing import List
import attr


@attr.s(auto_attribs=True)
class HacsManifest:
    """HacsManifest class."""

    name: str = ""
    content_in_root: bool = False
    zip_release: bool = False
    filename: str = None
    manifest: dict = {}
    domains: List[str] = []
    country: List[str] = []
    homeassistant: str = None
    persistent_directory: str = None
    iot_class: str = None
    render_readme: bool = False

    @staticmethod
    def from_dict(manifest: dict):
        """Set attributes from dicts."""
        return HacsManifest(
            manifest=manifest,
            name=manifest.get("name"),
            content_in_root=manifest.get("content_in_root"),
            filename=manifest.get("filename"),
            domains=manifest.get("domains"),
            country=manifest.get("country"),
            homeassistant=manifest.get("homeassistant"),
            persistent_directory=manifest.get("persistent_directory"),
            iot_class=manifest.get("iot_class"),
            render_readme=manifest.get("render_readme"),
        )
