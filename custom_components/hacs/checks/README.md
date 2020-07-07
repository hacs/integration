# Repository checks

This is where the checks that run against the various repository categories live.

## Structure

- All checks are in the directory for their category.
- Checks that aplies to all categories are in the `common` directory.
- There is one file pr. check.
- All checks needs tests to verify every possible outcome for the check.
- It's better with multiple files than a big check.
- All checks uses `RepositoryCheck` or `RepositoryActionCheck` as the base class.
- The `RepositoryActionCheck` are for checks that will breaks compatibility with with existing repositories (default), so these are only run in github actions.
- The class name should describe what the check does.
- Only use `check` or `async_check` methods to define checks.
- If a check should fail, raise `RepositoryCheckException` with the failure message.


## Example

```python
from custom_components.hacs.helpers.classes.check import (
    RepositoryActionCheck,
    RepositoryCheck,
    RepositoryCheckException,
)


class AwesomeRepository(RepositoryCheck):
    def check(self):
        if self.repository != "awesome":
            raise RepositoryCheckException("The repository is not awesome")

class SuperAwesomeRepository(RepositoryActionCheck):
    async def async_check(self):
        if self.repository != "super-awesome":
            raise RepositoryCheckException("The repository is not super-awesome")
```