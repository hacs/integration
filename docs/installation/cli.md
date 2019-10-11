---
id: cli
title: CLI Installation
sidebar_label: CLI Installation
---

To download via terminal, make sure you have `git` installed.

Next, Navigate to your custom_components directory:

`cd /config/custom_components` (This location is different from installation to installation, but since you are using CLI you knoe this.)

Then run the following commands:

```bash
git clone https://github.com/custom-components/hacs.git hacs_temp
cd hacs_temp
git checkout $(git describe --tags --always $(git rev-list --tags --max-count=1000) | grep -e "[0-9]\+\.[0-9]\+\.[0-9]\+$" | head -n 1)
cd ../
cp -r hacs_temp/custom_components/hacs hacs
rm -R hacs_temp
```

Restart Home Assistant once before moving on to the configuration ([UI](configuration/ui.md) / [YAML](configuration/yaml.md)).
