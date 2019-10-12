---
id: include
title: Include default repositories
---

As a developer you can now add your repository to be included in as a default repository in the store.

Before you try to add your repository to the default store first make sure that it follows the requirements for that type that are listed below.

Only the owner of the repository or a major contributor to it can submit a PR to have it included as a default.

When all of this is covered, you can add it to repository type files in the [`data` branch](https://github.com/custom-components/hacs/blob/data/repositories)

_NB!: The list is case sensitive._

When a PR for this is merged, it will show up in HACS after the first scheduled scan (every 800min).