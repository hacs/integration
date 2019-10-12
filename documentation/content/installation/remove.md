---
id: remove
title: Remove
---

If you want to remove HACS you need to to do that using the folowing steps.


1. Remove the configuration from `configuration.yaml`(if configured with legacy(YAMl)) or remove it using the trashbin icon on the integration page.
1. Restart Home Assistant **important**
1. Restart Home Assistant (yes, this needs to be done twice) **important**
1. Delete the `hacs` directory under `custom_components`.
1. Delete all files containing `hacs` under the `.storage` directory.
1. Restart Home Assistant.