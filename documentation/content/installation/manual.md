---
id: manual
title: Installation
---

This guide will take you though all the steps you need to install HACS.

### Step 1 - Open browser

_You are probably looking at this in a browser, so we can probably check this off._

### Step 2 - Go to the HACS repository

Then find the latest release from the release page.

Shortcut: [https://github.com/custom-components/hacs/releases/latest](https://github.com/custom-components/hacs/releases/latest)

### Step 3 - Initialize Download

Initialize the download by clicking on the "hacs.zip" link at the bottom of the page.

![install2](/img/install2.png)

### Step 4 - Extract the content

There should now be a `hacs.zip` file in your Download folder.

You need to unzip this, before proceeding.

### Step 5 - Move along

Now that you have extracted that file you will see something like this:

![install3](/img/install3.png)


The folder named `hacs` would need to be copied to your Home Assistant installation.

For this use your favorite tool to get stuff to Home Assistant.

If this is your first custom_component you would need to create a new folder (see [step 6](#step-6---bonus)).

If this is not your first, you should know where to place the `hacs` folder, and if this is not your first why are you reading this? you have done this earlier and should know this by now :D

Anyway the `hacs` folder needs to be placed under `<config_dir>/custom_components/`

On Hassio the final location will be `/config/custom_components/hacs`

On Hassbian(venv) the final location will be `/home/homeassistant/.homeassistant/custom_components/hacs`

### Step 6 - (Bonus)

If you are a seasoned user, skip to step 7.

Cool you are still reading.

Open the folder where you have your `configuration.yaml` file.
Don't open that file (yet) just the folder for now.

If you see a folder named `custom_components` there, go back to Step 5 if you think you need to do something here.

If you **do not** see a `custom_components` folder in **the same** folder as `configuration.yaml`, you need to create it.

The `custom_components` **needs** to be in **the exact same** folder as `configuration.yaml`

### Step 7 - Restart Home Assistant

Restart Home Assistant once before moving on to step 8.

### Step 8 - ✏️

You should now be done, next part will be to add it to your [configuration](configuration/start.md).
