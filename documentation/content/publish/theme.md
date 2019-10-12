---
id: theme
title: Themes
---

A template to use as a reference is [home-assistant-community-themes/template](https://github.com/home-assistant-community-themes/template)

This is for the [`frontend` integration in Home Assistant](https://www.home-assistant.io/components/frontend/)

## Requirements

For a theme repository to be valid these are the requirements:

### Repository structure

- The theme configuration file are located here `ROOT_OF_THE_REPO/themes/SCRIPT_NAME.yaml`
- There is only one theme configuration file (one directory under `ROOT_OF_THE_REPO/themes/`) per repository (if you have more, only the first one will be managed.)

#### OK example:

```text
themes/awesome.yaml
info.md
README.md
```

#### Not OK example:

```text
awesome.py
info.md
README.md
```

### GitHub releases (optional)

#### If there are releases

When installing/upgrading it will scan the content in the latest release.

If there are multiple releases in the repository the user have some options to install a specific version.
The choices will be the last 5 releases and the default branch.

#### If there are no releases

It will scan files in the branch marked as default.
