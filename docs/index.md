***

[**HOME**](/hacs/) | [INSTALLATION](/hacs/install) | [CONFIGURATION](/hacs/configure) | [TOKEN](/hacs/token)

***

# HACS (Home Assistant Community Store)

![hacsdemo](images/hacsdemo.gif)

## What is it?

This is a manager for your custom integration (components) and plugin (lovelace elements) needs.

It can help you download and update elements.

It cam also help you discover new awesome stuff.

## Updates

It checks for updates every 500 minutes after Home Assistant is started, you can also force a check by clicking the "RELOAD DATA" button under the "SETTINGS" tab.

## Logs

Like any other integration this logs to the `home-assistant.log` file.

You can also click the "OPEN LOG" form the "SETTINGS" tab to show logs only related to this integration (useful when creating a issue)

## Existing elements

This will not scan you local file system for existing elements.

Why?

Trust. If this did not download it, it can not know which version you have, so for elements you already have you still need to click the "INSTALL" button for that element.

## Data

All data it handles are saved to the `hacs` file that is located under `.storage`

## Note for developers

For your repository to be added there is a few criterias that needs to be met.

[See here for how to add a custom repository.](#add-custom-repos)

The description for each element are gathered from the description of the repository.

The version it shows/uses are gathered from the tag name of the latest release.

If you want to add a richer experience for your users you can add some extra files to the root of your repository (this is optional).

filename | description
-- | --
`example.yaml` | A configuration example for your element.
`example.png` | A Sample image of how this can look.

### Note for integration developers

For a integration repository to be valid these are the criterias:

- The repository uses GitHub releases
- There is only one element pr repository (if you have more, only the first one will be managed.)
- The integration (all the python files for it) are located under `ROOT_OF_THE_REPO/custom_components/INTEGRATION_NAME/`
- In that integration directory, there is a [`manifest.json`](https://developers.home-assistant.io/docs/en/creating_integration_manifest.html) file.

### Note for plugin developers

For a integration repository to be valid these are the criterias:

- The repository uses GitHub releases
- There are `.js` files under `ROOT_OF_THE_REPO/dist/` or directly in the root of the repo.
- One of the `.js` files have the same name as the repository.

It will first check the `dist` directory, if nothing there it will check the root. All `.js` files it find will be downloaded.

## Settings

This section is for the settings tab.

### Add custom repos

By default all elements that meet the requirements from these orgs are automatically added:

- [custom-components](https://github.com/custom-components)
- [custom-cards](https://github.com/custom-cards)

But you can add any other repository that meed the requirements, to do so go to the "SETTINGS" tab.

![settings](images/settings.png)

Add the url to the repository under "Custom integration repo's" or "Custom plugin repo's" depending on the type.

After you add a repository it will scan that repository, if it can be tracked the element from it will show up under "STORE".

Want to get inspiration on what to add, check out the [Awesome Home Assistant list](https://www.awesome-ha.com/) it has has links to some custom_components (integration) and custom_cards (plugin).

## Contribute

This integration is **massive** there are a lot of areas to contribute to.

Contributions to the docs, will almost be blindly accepted.

### For contributions to the integration itself (backend/frontend)

If the contribution is minor, do the change and open a PR (Pull Request).

For new features / Changes to existing features or other big changes, please open an RFC (Request for comment) issue before you start the work.

***

# Image "galery"

## Overview

![overview](images/overview.png)

## Store

![store](images/store.png)

## Settings

![settings](images/settings.png)

## Example integration

![example_integration](images/example_integration.png)

## Example plugin

![example_plugin](images/example_plugin.png)