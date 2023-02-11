"""Update the manifest file."""
import json
import os
from pathlib import Path
import sys

MANIFEST_FILE = Path(f"{os.getcwd()}/custom_components/hacs/manifest.json")


def update_manifest():
    """Update the manifest file."""
    version = "0.0.0"
    for index, value in enumerate(sys.argv):
        if value in ["--version", "-V"]:
            version = sys.argv[index + 1]

    with open(MANIFEST_FILE, encoding="utf-8") as manifestfile:
        base: dict = json.load(manifestfile)
        base["version"] = version

    with open(MANIFEST_FILE, "w", encoding="utf-8") as manifestfile:
        manifestfile.write(
            json.dumps(
                {
                    "domain": base["domain"],
                    "name": base["name"],
                    **{k: v for k, v in sorted(base.items()) if k not in ("domain", "name")},
                },
                indent=4,
            )
        )


update_manifest()
