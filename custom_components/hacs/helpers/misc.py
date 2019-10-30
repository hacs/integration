"""Helper functions: misc"""
# from distutils.version import LooseVersion
import semantic_version
from custom_components.hacs.repositories.manifest import HacsManifest


def get_repository_name(
    hacs_manifest: type(HacsManifest),
    repository_name: str,
    category: str = None,
    manifest: dict = None,
) -> str:
    """Return the name of the repository for use in the frontend."""

    if hacs_manifest.name is not None:
        return hacs_manifest.name

    if category == "integration":
        if manifest:
            if "name" in manifest:
                return manifest["name"]

    return repository_name.replace("-", " ").replace("_", " ").title()


def version_is_newer_than_version(new: str, old: str) -> bool:
    """Return a bool if source is newer than target, will also be true if identical."""
    if new == old:
        return True
    return semantic_version.Version.coerce(new) > semantic_version.Version.coerce(old)
