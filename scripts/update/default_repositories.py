"""Update the shipped default repositories data file."""
import json
import os
import sys


def update():
    """Update the shipped default repositories data file."""
    storage, to_store, old = None, {}, {}
    updated = 0

    with open(f"{os.getcwd()}/.storage/hacs.repositories", encoding="utf-8") as storage_file:
        storage = json.load(storage_file)

    with open(
        f"{os.getcwd()}/custom_components/hacs/utils/default.repositories", encoding="utf-8"
    ) as old_file:
        old = json.load(old_file)

    if storage is None:
        sys.exit("No storage file")

    for repo in storage["data"]:
        storage["data"][repo]["first_install"] = True
        for key in ("installed", "show_beta", "new"):
            storage["data"][repo][key] = False
        for key in ("installed_commit", "selected_tag", "version_installed"):
            storage["data"][repo][key] = None

        if old.get(repo, {}).get("etag_repository") != storage["data"][repo].get("etag_repository"):
            updated += 1

        to_store[repo] = storage["data"][repo]

    with open(
        f"{os.getcwd()}/custom_components/hacs/utils/default.repositories",
        mode="w",
        encoding="utf-8",
    ) as to_store_file:
        to_store_file.write(json.dumps(to_store))

    print(f"{updated} was updated")


if __name__ == "__main__":
    update()
