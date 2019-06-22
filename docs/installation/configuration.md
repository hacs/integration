# Configuration

**NB! This needs to be in `configuration.yaml`, _not_ in a "package".**

## Example configuration

```yaml
hacs:
  token: d73jds8f73jkr9d8sufv2br8sd9fy92nr9f80u23r97fhse
```

key | optional | default | description
-- | -- | -- | --
`token` | False | | A Github Personal Access Token
`appdaemon` | True | `False` | Enable tracking of AppDaemon apps.
`python_script` | True | `False` | Enable tracking of python scripts.
`theme` | True | `False` | Enable tracking of themes.

***

## Github Personal Access Token

_You need to generate an Access Token to your account before you start using this._

### Step 1 - Open browser

_You are probably looking at this in a browser, so we can probably check this off._

### Step 2 - Go to your GitHub "Developer settings"

_And then "Personal access tokens."_
or click here: [https://github.com/settings/tokens](https://github.com/settings/tokens)


### Step 3 - Start generation

Click the "Generate new token" button.

![token1](../images/token1.png)

_If you are asked to login, do so._

![token2](../images/token2.png)

### Step 4 - Choices

First give it a logical name so that you can recognize it.

Then click the "Generate token" button at the bottom.

You **do not** need to check _any_ of the boxes.

![token3](../images/token3.png)

### Step 5 - Copy

Now you see the generated token, this will be the **only** time you see it, make sure that you copy it manually or by clicking the clipboard icon.

![token4](../images/token4.png)

<!-- Disable sidebar -->
<style>.bs-sidebar{display: none !important}</style>
<!-- Disable sidebar -->