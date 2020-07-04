import json
import os

import requests

harequire = []
request = requests.get(
    "https://raw.githubusercontent.com/home-assistant/home-assistant/dev/setup.py"
)
request = request.text.split("REQUIRES = [")[1].split("]")[0].split("\n")
for req in request:
    if "=" in req:
        harequire.append(req.split(">")[0].split("=")[0].split('"')[1])

print(harequire)

with open(f"{os.getcwd()}/custom_components/hacs/manifest.json") as manifest:
    manifest = json.load(manifest)
    requirements = []
    for req in manifest["requirements"]:
        requirements.append(req.split(">")[0].split("=")[0])
    manifest["requirements"] = requirements
with open(f"{os.getcwd()}/requirements.txt") as requirements:
    tmp = requirements.readlines()
    requirements = []
    for req in tmp:
        requirements.append(req.replace("\n", ""))
for req in requirements:
    if req.split(">")[0].split("=")[0] in manifest["requirements"]:
        manifest["requirements"].remove(req.split(">")[0].split("=")[0])
        manifest["requirements"].append(req)

for req in manifest["requirements"]:
    if req.split(">")[0].split("=")[0] in harequire:
        print(f"{req.split('>')[0].split('=')[0]} in HA requirements, no need here.")
print(json.dumps(manifest["requirements"], indent=4, sort_keys=True))
with open(f"{os.getcwd()}/custom_components/hacs/manifest.json", "w") as manifestfile:
    manifestfile.write(json.dumps(manifest, indent=4, sort_keys=True))
