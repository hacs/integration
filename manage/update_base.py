"""Update the base file."""
import json
import os


def update_base():
    """Update base file."""
    with open("/tmp/config/.storage/hacs.repositories") as repositories_file:
        repositories = json.load(repositories_file)

    del repositories["data"]["172733314"]  # Remove HACS itself

    with open(
        f"{os.getcwd()}/custom_components/hacs/helpers/base.json", "w"
    ) as base_file:
        base_file.write(json.dumps(repositories["data"]))


update_base()