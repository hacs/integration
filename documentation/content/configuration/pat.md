---
id: pat
title: Github Personal Access Token
---

In order to work, HACS needs to retrieve information about repositories using Github's API.

Because of the [rate limits set by Github](https://developer.github.com/v3/#rate-limiting), HACS needs to be authenticated by a Personal Access Token, that you can generate using the following steps.

This token will have read-only access to public information, and will only be used by HACS to call Github's API.

## Step 1 - Open browser

_You are probably looking at this in a browser, so we can probably check this off._

## Step 2 - Go to your GitHub "Developer settings"

_And then "Personal access tokens."_
or click here: [https://github.com/settings/tokens](https://github.com/settings/tokens)


## Step 3 - Start generation

Click the "Generate new token" button.

![token1](/img/token1.png)

_If you are asked to login, do so._

![token2](/img/token2.png)

## Step 4 - Choices

First give it a logical name so that you can recognize it.

Then click the "Generate token" button at the bottom.

You **do not** need to check _any_ of the boxes.

![token3](/img/token3.png)

## Step 5 - Copy

Now you see the generated token, this will be the **only** time you see it, make sure that you copy it manually or by clicking the clipboard icon.

![token4](/img/token4.png)
