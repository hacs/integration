"""Initialize the HACS base."""
# pylint: disable=unused-argument, bad-continuation
import json
import uuid
from datetime import timedelta

from homeassistant.helpers.event import async_call_later, async_track_time_interval

from aiogithubapi import AIOGitHubException, AIOGitHubRatelimit
from integrationhelper import Logger


from ..const import ELEMENT_TYPES
from ..store import async_load_from_store, async_save_to_store
from ..helpers.get_defaults import get_default_repos_lists, get_default_repos_orgs


class HacsStatus:
    """HacsStatus."""

    startup = False
    background_task = False
    reloading_data = False
    upgrading_all = False


class HacsCommon:
    """Common for HACS."""

    categories = []
    blacklist = []
    default = []
    installed = []
    skip = []


class System:
    """System info."""

    status = HacsStatus()
    config_path = None
    new = False
    ha_version = None
    disabled = False
    lovelace_mode = "storage"


class Developer:
    """Developer settings/tools."""

    template_id = "Repository ID"
    template_content = ""
    template_raw = ""

    @property
    def devcontainer(self):
        """Is it a devcontainer?"""
        import os

        if "DEVCONTAINER" in os.environ:
            return True
        return False


class Hacs:
    """The base class of HACS, nested thoughout the project."""

    token = f"{str(uuid.uuid4())}-{str(uuid.uuid4())}"
    hacsweb = f"/hacsweb/{token}"
    hacsapi = f"/hacsapi/{token}"
    repositories = []
    repo = None
    data_repo = None
    developer = Developer()
    data = None
    configuration = None
    logger = Logger("hacs")
    github = None
    hass = None
    version = None
    system = System()
    tasks = []
    common = HacsCommon()

    @staticmethod
    def init(hass, github_token):
        """Return a initialized HACS object."""
        return Hacs()

    def get_by_id(self, repository_id):
        """Get repository by ID."""
        try:
            for repository in self.repositories:
                if repository.information.uid == repository_id:
                    return repository
        except Exception:  # pylint: disable=broad-except
            pass
        return None

    def get_by_name(self, repository_full_name):
        """Get repository by full_name."""
        try:
            for repository in self.repositories:
                if repository.information.full_name == repository_full_name:
                    return repository
        except Exception:  # pylint: disable=broad-except
            pass
        return None

    def is_known(self, repository_full_name):
        """Return a bool if the repository is known."""
        for repository in self.repositories:
            if repository.information.full_name == repository_full_name:
                return True
        return False

    @property
    def sorted_by_name(self):
        """Return a sorted(by name) list of repository objects."""
        return sorted(self.repositories, key=lambda x: x.display_name)

    @property
    def sorted_by_repository_name(self):
        """Return a sorted(by repository_name) list of repository objects."""
        return sorted(self.repositories, key=lambda x: x.information.full_name)

    async def register_repository(self, full_name, category, check=True):
        """Register a repository."""
        from ..repositories.repository import RERPOSITORY_CLASSES

        if full_name in self.common.skip:
            if full_name != "hacs/integration":
                self.logger.debug(f"Skipping {full_name}")
                return

        if category not in RERPOSITORY_CLASSES:
            self.logger.error(f"{category} is not a valid repository category.")
            return False

        repository = RERPOSITORY_CLASSES[category](full_name)
        if check:
            try:
                await repository.registration()
                if self.system.new:
                    repository.status.new = False
                if repository.validate.errors:
                    self.common.skip.append(repository.information.full_name)
                    if not self.system.status.startup:
                        self.logger.error(f"Validation for {full_name} failed.")
                    return repository.validate.errors
                repository.logger.info("Registration complete")
            except AIOGitHubException as exception:
                self.logger.debug(self.github.ratelimits.remaining)
                self.logger.debug(self.github.ratelimits.reset_utc)
                self.common.skip.append(repository.information.full_name)
                if not self.system.status.startup:
                    self.logger.error(
                        f"Validation for {full_name} failed with {exception}."
                    )
                return exception
        self.hass.bus.async_fire(
            "hacs/repository",
            {
                "id": 1337,
                "action": "registration",
                "repository": repository.information.full_name,
                "repository_id": repository.information.uid,
            },
        )
        self.repositories.append(repository)

    async def startup_tasks(self):
        """Tasks tha are started after startup."""
        self.system.status.background_task = True
        self.hass.bus.async_fire("hacs/status", {})
        self.logger.debug(self.github.ratelimits.remaining)
        self.logger.debug(self.github.ratelimits.reset_utc)

        await self.handle_critical_repositories_startup()
        await self.handle_critical_repositories()
        await self.load_known_repositories()
        await self.clear_out_blacklisted_repositories()

        self.tasks.append(
            async_track_time_interval(
                self.hass, self.recuring_tasks_installed, timedelta(minutes=30)
            )
        )
        self.tasks.append(
            async_track_time_interval(
                self.hass, self.recuring_tasks_all, timedelta(minutes=800)
            )
        )

        self.hass.bus.async_fire("hacs/reload", {"force": True})
        await self.recuring_tasks_installed()

        self.system.status.startup = False
        self.system.status.background_task = False
        self.hass.bus.async_fire("hacs/status", {})
        await self.data.async_write()

    async def handle_critical_repositories_startup(self):
        """Handled critical repositories during startup."""
        alert = False
        critical = await async_load_from_store(self.hass, "critical")
        if not critical:
            return
        for repo in critical:
            if not repo["acknowledged"]:
                alert = True
        if alert:
            self.logger.critical("URGENT!: Check the HACS panel!")
            self.hass.components.persistent_notification.create(
                title="URGENT!", message="**Check the HACS panel!**"
            )

    async def handle_critical_repositories(self):
        """Handled critical repositories during runtime."""
        # Get critical repositories
        instored = []
        critical = []
        was_installed = False

        try:
            critical = await self.data_repo.get_contents("critical")
            critical = json.loads(critical.content)
        except AIOGitHubException:
            pass

        if not critical:
            self.logger.debug("No critical repositories")
            return

        stored_critical = await async_load_from_store(self.hass, "critical")

        for stored in stored_critical or []:
            instored.append(stored["repository"])

        stored_critical = []

        for repository in critical:
            self.common.blacklist.append(repository["repository"])
            repo = self.get_by_name(repository["repository"])

            stored = {
                "repository": repository["repository"],
                "reason": repository["reason"],
                "link": repository["link"],
                "acknowledged": True,
            }

            if repository["repository"] not in instored:
                if repo is not None and repo.installed:
                    self.logger.critical(
                        f"Removing repository {repository['repository']}, it is marked as critical"
                    )
                    was_installed = True
                    stored["acknowledged"] = False
                    # Uninstall from HACS
                    repo.remove()
                    await repo.uninstall()
            stored_critical.append(stored)

        # Save to FS
        await async_save_to_store(self.hass, "critical", stored_critical)

        # Resart HASS
        if was_installed:
            self.logger.critical("Resarting Home Assistant")
            self.hass.async_create_task(self.hass.async_stop(100))

    async def recuring_tasks_installed(self, notarealarg=None):
        """Recuring tasks for installed repositories."""
        self.logger.debug(
            "Starting recuring background task for installed repositories"
        )
        self.system.status.background_task = True
        self.hass.bus.async_fire("hacs/status", {})
        self.logger.debug(self.github.ratelimits.remaining)
        self.logger.debug(self.github.ratelimits.reset_utc)
        for repository in self.repositories:
            if repository.status.installed:
                try:
                    await repository.update_repository()
                    repository.logger.debug("Information update done.")
                except AIOGitHubException:
                    self.system.status.background_task = False
                    self.hass.bus.async_fire("hacs/status", {})
                    await self.data.async_write()
                    self.logger.debug(
                        "Recuring background task for installed repositories done"
                    )
                    return
        await self.handle_critical_repositories()
        self.system.status.background_task = False
        self.hass.bus.async_fire("hacs/status", {})
        await self.data.async_write()
        self.logger.debug("Recuring background task for installed repositories done")

    async def recuring_tasks_all(self, notarealarg=None):
        """Recuring tasks for all repositories."""
        self.logger.debug("Starting recuring background task for all repositories")
        self.system.status.background_task = True
        self.hass.bus.async_fire("hacs/status", {})
        self.logger.debug(self.github.ratelimits.remaining)
        self.logger.debug(self.github.ratelimits.reset_utc)
        for repository in self.repositories:
            try:
                await repository.update_repository()
                repository.logger.debug("Information update done.")
            except AIOGitHubException:
                self.system.status.background_task = False
                self.hass.bus.async_fire("hacs/status", {})
                await self.data.async_write()
                self.logger.debug("Recuring background task for all repositories done")
                return
        await self.load_known_repositories()
        await self.clear_out_blacklisted_repositories()
        self.system.status.background_task = False
        await self.data.async_write()
        self.hass.bus.async_fire("hacs/status", {})
        self.hass.bus.async_fire("hacs/repository", {"action": "reload"})
        self.logger.debug("Recuring background task for all repositories done")

    async def clear_out_blacklisted_repositories(self):
        """Clear out blaclisted repositories."""
        need_to_save = False
        for repository in self.common.blacklist:
            if self.is_known(repository):
                repository = self.get_by_name(repository)
                if repository.status.installed:
                    self.logger.error(
                        f"You have {repository.information.full_name} installed with HACS "
                        + "this repository has been blacklisted, please consider removing it."
                    )
                else:
                    need_to_save = True
                    repository.remove()

        if need_to_save:
            await self.data.async_write()

    async def get_repositories(self):
        """Return a list of repositories."""
        repositories = {}
        for category in self.common.categories:
            repositories[category] = await get_default_repos_lists(
                self.github, category
            )
            org = await get_default_repos_orgs(self.github, category)
            for repo in org:
                repositories[category].append(repo)

        for category in repositories:
            for repo in repositories[category]:
                if repo not in self.common.default:
                    self.common.default.append(repo)
        return repositories

    async def load_known_repositories(self):
        """Load known repositories."""
        self.logger.info("Loading known repositories")
        repositories = await self.get_repositories()

        for item in await get_default_repos_lists(self.github, "blacklist"):
            if item not in self.common.blacklist:
                self.common.blacklist.append(item)

        for category in repositories:
            for repo in repositories[category]:
                if repo in self.common.blacklist:
                    continue
                if self.is_known(repo):
                    continue
                try:
                    await self.register_repository(repo, category)
                except (AIOGitHubException, AIOGitHubRatelimit):
                    pass
