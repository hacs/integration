# HACS (Home Assistant Community Store)

![hacsdemo](images/hacsdemo.gif)

***

## What can HACS do?

This is a manager for your custom Home Assistant needs.

It can help you download and update elements.

It can also help you discover new awesome stuff.

### What can it track/discover?

- Custom integrations (components/platforms/custom_component) for Home Assistant
- Custom plugins (cards/rows/mods) for Lovelace
- AppDaemon apps for [AppDaemon](https://appdaemon.readthedocs.io/en/latest/)
- Themes for the [frontend integration](https://www.home-assistant.io/components/frontend/) in Home Assistant
- "python_scripts" for the [`python_scripts` integration](https://www.home-assistant.io/components/python_script/) in Home Assistant

## Updates

### Installed elements

HACS will check for updates to installed elements:

- At startup.
- Every 30 minutes after HA startup.

### Everything else

HACS will check for updates to every element:

- At startup
- Every 500 minutes after HA startup.

### Manually trigger updates

You can also force a check by clicking the "RELOAD DATA" button under the "SETTINGS" tab _(This will force a reload of everything.)_

Under the "SETTINGS" tab there is also a reload icon to the left of every custom repository you have added, clicking that will reload info for it.

On each RepositoryView (the page with details about the element) there is a reload icon at the top-right corner, clicking that will reload it.

## Logs

Like any other integration this logs to the `home-assistant.log` file.

You can also click the "OPEN LOG" from the "SETTINGS" tab to show logs only related to this integration (useful when creating a issue)

To enable `debug` logging, add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    hacs: debug
```

## Startup

During the startup it will scan for know repositories, and there will be a progressbar indicating that it's working.

![startup](images/bg_task.PNG)

This is completely normal, and you can still use it while it's working.
The same indication will show when a scheduled task is running.

## Existing elements

This will not scan you local file system for existing elements.

Why?

Trust. If this did not download it, there'd be no way to know which version you have, so for elements you already have you will still need to click the "INSTALL" button for that element.

## Local data storage

All data it handles are saved to `hacs.*` files that is located under `.storage`

## HACS Sensor

During the setup HACS will add a new sensor to your installation (`sensor.hacs`).
This will have the number of pending updates as the state.

![sensor](https://user-images.githubusercontent.com/15093472/59136215-5ff29d00-8982-11e9-860f-75d382a4d3b7.png)

***

## Contribute

This integration is **massive** and there are a lot of areas to contribute to.

Contributions to the docs, will almost be blindly accepted.

_Contributions for the documentation should go against the `master` branch._

### For contributions to the integration itself (backend/frontend)

_Contributions for the integration should go against the `master` branch._

If the contribution is minor, make the change and open a PR (Pull Request).

For new features, changes to existing features, or other big changes, please open an RFC (Request for comment) issue before you start the work.

### Translations

Starting with version 0.15.0 there is now a new experimental UI for HACS, this have support for translations 🎉

To handle submissions of translated strings we are using [Lokalise](https://lokalise.com) they provide us with an amazing platform that is easy to use and maintain.

![Lokalise](images/lokalise.png)

To help out with the translation of HACS you need an account on Lokalise, the easiest way to get one is to [click here](https://lokalise.com/login/) then select "Log in with GitHub".

When you have created your account [click here to join the HACS project on Lokalise.](https://lokalise.co/signup/190570815d9461966ae081.06523141/all/)

If you are unsure on how to proceed their documentation is really good, and you can [find that here.](https://docs.lokalise.com/en/) or send me a message @ discord (username: `ludeeus#4212`)

If you want to add translations for a language that is not listed please [open a FR here](https://github.com/custom-components/hacs/issues/new?template=feature_request.md)

Before each release new translations are pulled from Lokalise, so if you have added something look for it in the next version of HACS.

If you add elements to the UI of HACS that needs translations, update the [`strings.json`](https://github.com/custom-components/hacs/blob/master/custom_components/hacs/strings.json) file, when your PR are merged those new keys will be added to Lokalise ready to be translated.

### Devcontainer

[The easiest way to contribute is to spin up a devcontainer.](https://code.visualstudio.com/docs/remote/containers) with VSCode, it has all the tools you need included, and it does not interfare with your system.

**Requirements:**

- Docker
- VS Code
- Remote - Containers (VS Code extension)

Make your changes, then run the task "Start Home Assistant" to test them, HA will run on port 8124.
