import os
import json

with open(f"{os.getcwd()}/custom_components/hacs/manifest.json", "r") as manifest:
    manifest = json.load(manifest)
    requirements = []
    for req in manifest["requirements"]:
        requirements.append(req.split(">")[0].split("=")[0])
    manifest["requirements"] = requirements

with open(f"{os.getcwd()}/requirements.txt", "r") as requirements:
    tmp = requirements.readlines()
    requirements = []
    for req in tmp:
        requirements.append(req.replace("\n", ""))

for req in requirements:
    if req.split(">")[0].split("=")[0] in manifest["requirements"]:
        manifest["requirements"].remove(req.split(">")[0].split("=")[0])
        manifest["requirements"].append(req)

print(json.dumps(manifest["requirements"], indent=4, sort_keys=True))

with open(f"{os.getcwd()}/custom_components/hacs/manifest.json", "w") as manifestfile:
    manifestfile.write(json.dumps(manifest, indent=4, sort_keys=True))
