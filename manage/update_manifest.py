"""Update the manifest file."""
import sys
import json
import os


def update_manifest():
    """Update the manifest file."""
    version = "0.0.0"
    for index, value in enumerate(sys.argv):
        if value in ["--version", "-V"]:
            version = sys.argv[index + 1]

    with open(f"{os.getcwd()}/custom_components/hacs/manifest.json", "w") as manifest:
        manifest = json.load(manifest)
        manifest["version"] = version
        manifest.write(json.dumps(manifest, indent=4, sort_keys=True))


update_manifest()
