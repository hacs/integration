# Note for developers

For your repository to be added there are a few criteria that need to be met.

- See [Integration developer](../intgegration) for integrations.
- See [Plugin developer](../plugin) for plugins.

## Repository information

### Description

The description of the repository is also the same description that is shown in HACS.

### Topics

Repository topics are not displayed in HACS, but they can be used for searchablility in the HACS store.

## Versions

If the repository uses GitHub releases, the tagname from the latest release is used to set the remote version.

If the repository does not use those, the 7 first charachters of the last commit will be used.

## Enhance the experience

If you want to add a richer experience for your users you can add an `info.md` file to the root of your repository (this is optional), this file will be rendered under the repository description, it does not support the full styling options as Github so use with care.

Some examples of `info.md` files:

### [Compact Custom Header](https://github.com/maykar/compact-custom-header/blob/1.0.4b9/info.md)

  ![cch](../images/info_cch.PNG)

###[Lovelace Swipe Navigation](https://github.com/maykar/lovelace-swipe-navigation/blob/1.2.0/info.md)

![swipe](../images/info_swipe.PNG)

### [HomeAssistant-Atrea](https://github.com/JurajNyiri/HomeAssistant-Atrea/blob/2.1/info.md)  

![Atrea](../images/info_atrea.PNG)


### Want to add your repository to the store as a default?

[See here for how to add a custom repository.](../include_default_repositories)