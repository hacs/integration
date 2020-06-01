# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
class RepositoryPropertyCustom:

    @property
    def custom(self):
        """Return flag if the repository is custom."""
        if self.data.full_name.split("/")[0] in ["custom-components", "custom-cards"]:
            return False
        if str(self.data.id) in [str(x) for x in self.hacs.common.default]:
            return False
        if self.data.full_name == "hacs/integration":
            return False
        return True
