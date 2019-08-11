# FAQ

## What is HACS?

HACS is an abbreviation of "Home Assistant Community Store".

Although "Store" is not "technically" correct, since nothing is sold, it's more like a marketplace? but "HACM" didn't have the same ring to it.

### Highlights of what HACS can do

- Help you discover new custom elements.
- Help you install (download) new custom elements.
- Help you keep track of your custom elements.

***

## Is this for hass.io only?

No, it's not.

You can use this on _any_ Home Assistant installation.

_Windows might have issues, but if you are running HA on Windows you are probably used to that._

***

## How does it work: Installation

When you install an element this is what's happening:

1. The local target directory(folder) is deleted.
1. A new local target directory is created.
1. All expected files are downloaded to that directory.
1. The files it downloads depends on the type.

### Files downloaded for `appdaemon`

_Everything under the first directory in `apps`_

The files are downloaded to `<config_dir>/appdaemon/apps/*`

### Files downloaded for `integrations`

_Everything under the first directory in `custom_components`_


The files are downloaded to `<config_dir>/custom_components/*`

### Files downloaded for `plugins`

_Every `.js` file in the source directory, this can be on the release page, the `dist` directory, or the root of the repository._

_If it's the `dist` directory, it will download **any** file in that directory (and sub directories)._

When a `.js` file is downloaded, a compressed `.gz` version of if will be created, this file (if it exist) will be served to the requester to save transfer size/time.
If you make local changes to a plugin in the `.js` file, delete the `.gz` variant to have HACS serve up that one.


The files are downloaded to `<config_dir>/www/community/*`

### Files downloaded for `python_script`

The first file under the `python_scripts` directory._

The files are downloaded to `<config_dir>/python_scripts/*`

### Files downloaded for `theme`

The first file under the `themes` directory._

The files are downloaded to `<config_dir>/themes/*`

For this to work you need to include the themes directory like this:

```yaml
frontend:
  themes: !include_dir_merge_named themes
```

***

## How does it work: Upgrade

The same as installation.

***

## How can I install this.

Look at the [installation documentation.](../installation/manual/)

## Known limitations

- If you install/upgrade/remove or add a custom repository while the background task is running, do **not** restart Home Assistant until that task is done, if you do your action will not be saved.