# Repository checks

This is where the checks that run against the various repository categories live.

## Structure

- All checks are in the directory for their category.
- Checks that aplies to all categories are in the `common` directory.
- There is one file pr. check.
- All checks needs tests to verify every possible outcome for the check.
- It's better with multiple files than a big check.
- All checks uses `RepositoryCheck` as the base class.
- The class name should describe what the check does.
- Only use `check` or `async_check` methods to define checks.
- If a check is implemented that breaks compability with exsisting repositories (default), it can only be active if run as a github action (use the `self.action` property to check for that in the check)
- If a check should fail, raise `RepositoryCheckException` with the failure message.


## Example

```python
from custom_components.hacs.helpers.classes.check import (
    RepositoryCheck,
    RepositoryCheckException,
)


class AwesomeRepository(RepositoryCheck):
    def check(self):
        if not self.action:
            return
        if self.repository != "awesome":
            raise RepositoryCheckException("The repository is not awesome")

```