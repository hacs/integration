# Note for developers

For your repository to be added there are a few criteria that need to be met.

- [General requirements](#general-requirements)
- [Integration requirements](../integration) for integrations.
- [Plugin requirements](../plugin) for plugins.
- [AppDaemon requirements](../plugin) for AppDaemon apps.
- [Python_scripts requirements](../plugin) for python scripts.
- [Theme requirements](../plugin) for themes.

## General requirements

### Description

Your repository on GitHub needs to have a description that in short tell what the content in the repository do.

This description is also used in HACS.

### Topics

Your repository on GitHub needs to have topics, topics are not displayed in HACS, but they can be used for searchability in the HACS store.

### README

Your repository needs to have a readme with information about how to use it.
This is not used in HACS, but without this it's hard for the user to get started.

### [info.md](#info.md)

If you want to add a richer experience for your users you can add an `info.md` file to the root of your repository (this is optional, if you do not have this you need to set [`render_readme`](#hacsjson) in the `hacs.json` file), this file will be rendered under the repository description, it does not support the full styling options as Github so use with care.

[See the Templates section on how you can make this awesome](#templates)


### hacs.json

This is a special manifest file that both give information to HACS that are used in the UI, and tell it what to use and where it is, this file needs to be located in the root of your repository.

The following keys are supported:

Key | Required | Description.
-- | -- | --
name | True| The display name that will be used in the HACS UI
content_in_root | False | Boolean to indicate that the content is in the root of the repository.
filename | False | Name of the file HACS should look for, only applies to single item categories (plugin, theme, python_scripts)
render_readme | False | Tells HACS to render the README.md file instead of info.md
domains | False | A list of domains, `["sensor", "switch"]`
country | False | A2(ISO) variant of the country name <https://www.worldatlas.com/aatlas/ctycodes.htm>
homeassistant | False | The minimum required Home Assistant version
persistent_directory | False | This will only apply to integrations, a relative path (under the integration dir) that will be kept safe during upgrades.
iot_class | For integrations | The type of communication with the service/device

**examples:**

```json
{
  "name": "My awesome thing",
  "content_in_root": true,
  "filename": "my_super_awesome_thing.js",
  "country": ["NO", "SE", "DK"]
}
```

```json
{
  "name": "My awesome thing",
  "country": "NO",
  "domains": ["media_player", "sensor"],
  "homeassistant": "0.99.9",
  "persistent_directory": "userfiles"
}
```

#### key option `country`

This key can be a single value, or a list.

```
"country": ["NO", "SE", "DK"]
```

```
"country": "NO",
```


#### key option `iot_class`

This is only for integrations.

[Here you can use the same as Home Assistant uses](https://www.home-assistant.io/blog/2016/02/12/classifying-the-internet-of-things)


## Versions

If the repository uses GitHub releases, the tagname from the latest release is used to set the remote version. (**NB: just publishing tags is not enough, you need to publish releases)

If the repository does not use those, the 7 first characters of the last commit will be used.

### Templates

You can use Jijna2 templates to control what and how the info is displayed.
In addition to the default templates of Jijna these are added:

Template value | Description
-- | --
installed | True / False if it is installed.
pending_update | True / False if a update is pending.
prerelease | True / False if it's a pre release.
selected_tag | The selected version.
version_available | The latest available version.
version_installed | The installed version

#### Examples

##### Prerelease

```yaml
{% if prerelease %}
## NB!: This is a Beta version!
{% endif %}
```

![beta](../images/beta.png)

##### [Here Travel Time](https://github.com/eifinger/here_travel_time/blob/master/info.md)

```yaml
{% if installed %}
# Changes as compared to your installed version:

## Breaking Changes

## Changes

## Features

{% if version_installed.replace("v", "").replace(".","") | int < 141  %}
- Added `mode: bicycle`
- Added `mode: publicTransportTimeTable` - Please look [here](https://developer.here.com/documentation/routing/topics/public-transport-routing.html) for differences between the two public modes.
{% endif %}
{% if version_installed.replace("v", "").replace(".","") | int < 142  %}
- Release notes are shown in HACS depending on your installed version
{% endif %}

## Bugfixes

{% if version_installed.replace("v", "").replace(".","") | int < 143  %}
- Fix for `mode: publicTransportTimeTable` returning `No timetable route found`
{% endif %}
---
{% endif %}
```

![here](../images/info_jinja_here.png)

### Some examples of `info.md` files

#### [Compact Custom Header](https://github.com/maykar/compact-custom-header/blob/1.0.4b9/info.md)

  ![cch](../images/info_cch.PNG)

#### [Lovelace Swipe Navigation](https://github.com/maykar/lovelace-swipe-navigation/blob/1.2.0/info.md)

![swipe](../images/info_swipe.PNG)

#### [HomeAssistant-Atrea](https://github.com/JurajNyiri/HomeAssistant-Atrea/blob/2.1/info.md)  

![Atrea](../images/info_atrea.PNG)


### Want to add your repository to the store as a default?

[See here for how to add a custom repository.](../include_default_repositories)

## Badges

Tell your users that your repository can be tracked with HACS.

### Default repository

_If your repository is in the default store._

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

```
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
```

***

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

```
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
```

### Custom repository

_If your repository can be added as a custom repository._

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

```
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
```

***

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)


```
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
```
