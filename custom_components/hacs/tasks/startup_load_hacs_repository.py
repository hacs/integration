"""Starting setup task: load HACS repository."""
from ..enums import HacsDisabledReason, HacsStage
from ..exceptions import HacsException
from ..helpers.functions.information import get_repository
from ..helpers.functions.register_repository import register_repository
from .base import HacsTaskRuntimeBase


async def async_setup() -> None:
    """Set up this task."""
    return Task()


class Task(HacsTaskRuntimeBase):
    """Load HACS repositroy."""

    stages = [HacsStage.STARTUP]

    async def execute(self) -> None:
        try:
            repository = self.hacs.get_by_name("hacs/integration")
            if repository is None:
                await register_repository("hacs/integration", "integration")
                repository = self.hacs.get_by_name("hacs/integration")
            if repository is None:
                raise HacsException("Unknown error")
            repository.data.installed = True
            repository.data.installed_version = self.hacs.integration.version
            repository.data.new = False
            self.hacs.repository = repository.repository_object
            self.hacs.data_repo, _ = await get_repository(
                self.hacs.session, self.hacs.configuration.token, "hacs/default", None
            )
        except HacsException as exception:
            if "403" in f"{exception}":
                self.log.critical("GitHub API is ratelimited, or the token is wrong.")
            else:
                self.log.critical("[%s] - Could not load HACS!", exception)
            self.hacs.disable_hacs(HacsDisabledReason.LOAD_HACS)
