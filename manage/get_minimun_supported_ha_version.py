import os

with open(
    "/home/runner/work/integration/integration/custom_components/hacs/constrains.py",
    "r",
) as f:
    cfile = f.read()
    for line in cfile.splitlines():
        if "MINIMUM_HA_VERSION = " in line:
            print(line.split("MINIMUM_HA_VERSION = ")[-1].split(".")[1])

