# `python_script` developers

A template to use as a reference is [ps-hacs](https://github.com/ludeeus/ps-hacs)

This is for the [`python_script` integration in Home Assistant](https://www.home-assistant.io/components/python_script/)

## Requirements

For a python_script repository to be valid these are the requirements:

### Repository structure

- The python script are located here `ROOT_OF_THE_REPO/python_scripts/SCRIPT_NAME.py`
- There is only one python file (one directory under `ROOT_OF_THE_REPO/python_scripts/`) per repository (if you have more, only the first one will be managed.)

#### OK example:

```text
python_scripts/awesome.py
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

#### If there are no releases

It will scan files in the branch marked as default.

<!-- Disable sidebar -->
<script>document.getElementsByClassName("bs-sidebar").item(0).style.display = "none";</script>
<!-- Disable sidebar -->