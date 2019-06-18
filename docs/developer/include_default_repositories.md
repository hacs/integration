# Include default repositories

As a developer you can now add your repository to be included in as a default repository in the store.

Before you try to add your repository to the default store first make sure that it follows the requirements for that type that are listed below.

Only the owner of the repository or a major contributor to it can submit a PR to have it included as a default.

When all of this is covered, you can add it to `DEFAULT_REPOSITORIES` at the bottom of the [`const.py file`](https://github.com/custom-components/hacs/blob/master/custom_components/hacs/const.py)

When a PR for this is merged, it will be a part of the next planned minor release (0.X.0), if no release is planed a release will be created about a week after the first addition.

**Examples:**

- [`integration`](https://github.com/custom-components/hacs/pull/64)
- [`plugin`](https://github.com/custom-components/hacs/pull/65)