# Integration developers

A good template to use as a reference is [blueprint](https://github.com/custom-components/blueprint)

## Requirements

For a integration repository to be valid these are the requirements:

### Repository structure

- There is only one integration (one directory under `ROOT_OF_THE_REPO/custom_components/`) pr. repository (if you have more, only the first one will be managed.)
- The integration (all the python files for it) are located under `ROOT_OF_THE_REPO/custom_components/INTEGRATION_NAME/`
- There is only one integration (one directory under `ROOT_OF_THE_REPO/custom_components/`) per repository (if you have more, only the first one will be managed.)
- The integration and all the python files for it are located under `ROOT_OF_THE_REPO/custom_components/INTEGRATION_NAME/`

#### OK example:

```text
custom_components/awesome/__init_.py
custom_components/awesome/sensor.py
custom_components/awesome/manifest.py
info.md
README.md
```

#### Not OK example (1):

```text
awesome/__init_.py
awesome/sensor.py
awesome/manifest.py
info.md
README.md
```

#### Not OK example (2):

```text
__init_.py
sensor.py
manifest.py
info.md
README.md
```

### `manifest.json`

In the integration directory, there is a [`manifest.json`](https://developers.home-assistant.io/docs/en/creating_integration_manifest.html) file.

### GitHub releases (optional)

#### If there are releases

When installing/upgrading it will scan the content in the latest release.

#### If there are no releases

It will scan files in the branch marked as default.
