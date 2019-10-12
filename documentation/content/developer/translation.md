---
id: translation
title: Translation
---

To handle submissions of translated strings we are using [Lokalise](https://lokalise.com) they provide us with an amazing platform that is easy to use and maintain.

![Lokalise](/img/lokalise.png)

To help out with the translation of HACS you need an account on Lokalise, the easiest way to get one is to [click here](https://lokalise.com/login/) then select "Log in with GitHub".

When you have created your account [click here to join the HACS project on Lokalise.](https://lokalise.com/public/190570815d9461966ae081.06523141/)

If you are unsure on how to proceed their documentation is really good, and you can [find that here.](https://docs.lokalise.com/en/) or send me a message @ discord (username: `ludeeus#4212`)

If you want to add translations for a language that is not listed please [open a FR here](https://github.com/custom-components/hacs/issues/new?template=feature_request.md)

Before each release new translations are pulled from Lokalise, so if you have added something look for it in the next version of HACS.

If you add elements to the UI of HACS that needs translations, update the [`strings.json`](https://github.com/custom-components/hacs/blob/master/custom_components/hacs/strings.json) file, when your PR are merged those new keys will be added to Lokalise ready to be translated.
