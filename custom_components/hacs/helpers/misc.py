"""Helper functions: misc"""
from custom_components.hacs.repositories.manifest import HacsManifest


def get_repository_name(
    hacs_manifest: type(HacsManifest),
    repository_name: str,
    category: str = None,
    manifest: dict = None,
) -> str:
    """Return the name of the repository for use in the frontend."""

    if hacs_manifest.name != "":
        return hacs_manifest.name

    if category == "integration":
        if manifest:
            if "name" in manifest:
                return manifest["name"]

    return repository_name.replace("-", " ").replace("_", " ").title()
