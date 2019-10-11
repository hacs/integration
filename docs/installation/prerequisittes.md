---
id: prerequisittes
title: Prerequisittes
sidebar_label: Prerequisittes
---

- **You need to use Home Assistant version 0.97.0 or newer for the latest version of HACS to work. Check the release notes before you download as this page may be slightly out of date.**
- **If you move from [`custom_updater`](https://github.com/custom-components/custom_updater) to this see the special note at the bottom here.**



## Moving from custom_updater

If you have [`custom_updater`](https://github.com/custom-components/custom_updater) installed you need to remove that (rename the directory or delete it completely). You will also need to remove the custom_updater entry from your configuration.yaml file.

HACS and [`custom_updater`](https://github.com/custom-components/custom_updater) can not operate on the same installation.

If you used the special endpoint `/customcards/` endpoint for your Lovelace cards, you now need to reinstall that plugin using HACS and use the url provided in the page for that plugin in the HACS UI, if the plugin is not there you need to use `/local/` instead.

As noted under ['Existing elements'](basic/existing_elements.md) You need to click the "INSTALL" button for each element you previously have installed.