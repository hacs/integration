---
id: documentation
title: Documentation
---

[![Netlify Status](https://api.netlify.com/api/v1/badges/ec224ba7-b3fb-4fc6-929e-991ba9801b53/deploy-status)](https://app.netlify.com/sites/hacs/deploys)

The documentation site for HACS is build with [Docusaurus](https://docusaurus.io) and hosted on [Netlify](https://www.netlify.com/)

## Contribute to the documentation

There are two ways of contributing to the documentation:

- Using the "Edit this page" link at the bottom of every page.
- Locally changing (devcontainer)

All changes to the documentation should go against the `master` branch.

### Edit this page

When you see something that needs changing when you browse the documentation, scroll down to the bottom of the page you are looking at, and click the "Edit this page" link.

![edit](/img/edit_this.png)

This will take you to the GitHub page for it so you can cahnge the content.

### Locally changing (devcontainer)

First spinn up the [devcontainer](/docs/developer/devcontainer)

When you have that running issue the following comands:

```bash
cd documentation
npm install
npm start
```

You have now started a local webserver that hosts the documentation on http://localhost:3000

That server will reload if you do changes to the documentation so you can live see how the changes look.

When you are happy with the result, push the changes to your fork and create a PR to have it merged to the HACS base.

## Contents

All pages for the HACS documentation is located under:

```text
documentation/content/
```

## New pages

1. Create a new `.md` file under `documentation/content/` in a sub-directory that fits the purpose of the file.
1. Add a reference to that file in `documentation/sidebars.js`

At the top of all pages you should have this:

```text
---
id: A ID for that file, ie. 'feature' (lowercase)
title: A Title for the page, this will also be used in the sidebar, ie. Feature
---
```