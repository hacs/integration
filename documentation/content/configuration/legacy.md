---
id: legacy
title: Configure HACS with YAML
sidebar_label: YAML (legacy)
---

_This page assume that you have allready finished the [installation](/docs/installation/prerequisites)_

## Example configuration

```yaml
hacs:
  token: d73jds8f73jkr9d8sufv2br8sd9fy92nr9f80u23r97fhse (Don't copy+paste this token, create your own)
```

key | optional | default | description
-- | -- | -- | --
`token` | False | | [A Github Personal Access Token](/docs/configuration/pat)
`sidepanel_title` | True | Community | The name used for the sidepanel link.
`sidepanel_icon` | True | "mdi:alpha-c-box" | The icon used for the sidepanel link.
`appdaemon` | True | `False` | Enable tracking of AppDaemon apps.
`python_script` | True | `False` | Enable tracking of python scripts.
`theme` | True | `False` | Enable tracking of themes.
`options` | True |  | A map of options.

### Options (map)

```yaml
hacs:
  ...
  options:
    ...
```

option | description
-- | --
`country` | Set a filter based on your [A2(ISO) country code](https://www.worldatlas.com/aatlas/ctycodes.htm).
`release_limit` | Number of releases to show in the version selector. (Defaults to 5)
`experimental` | Boolean to enable experimental features (defaults to False).
