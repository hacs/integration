"""Data handler for HACS."""
from integrationhelper import Logger
from ..const import VERSION
from ..repositories.repository import HacsRepository
from ..repositories.manifest import HacsManifest
from ..store import async_save_to_store, async_load_from_store

from custom_components.hacs.globals import get_hacs, removed_repositories, get_removed
from custom_components.hacs.helpers.register_repository import register_repository


class HacsData:
    """HacsData class."""

    def __init__(self):
        """Initialize."""
        self.logger = Logger("hacs.data")
        self.hacs = get_hacs()

    async def async_write(self):
        """Write content to the store files."""
        if self.hacs.system.status.background_task or self.hacs.system.disabled:
            return

        self.logger.debug("Saving data")

        # Hacs
        await async_save_to_store(
            self.hacs.hass,
            "hacs",
            {
                "view": self.hacs.configuration.frontend_mode,
                "compact": self.hacs.configuration.frontend_compact,
                "onboarding_done": self.hacs.configuration.onboarding_done,
            },
        )

        await async_save_to_store(
            self.hacs.hass, "removed", [x.__dict__ for x in removed_repositories]
        )

        # Repositories
        content = {}
        for repository in self.hacs.repositories:
            if repository.repository_manifest is not None:
                repository_manifest = repository.repository_manifest.manifest
            else:
                repository_manifest = None
            content[repository.information.uid] = {
                "authors": repository.data.authors,
                "category": repository.data.category,
                "description": repository.data.description,
                "downloads": repository.releases.downloads,
                "full_name": repository.data.full_name,
                "first_install": repository.status.first_install,
                "hide": repository.status.hide,
                "installed_commit": repository.versions.installed_commit,
                "installed": repository.status.installed,
                "last_commit": repository.versions.available_commit,
                "last_release_tag": repository.versions.available,
                "last_updated": repository.information.last_updated,
                "name": repository.data.name,
                "new": repository.status.new,
                "repository_manifest": repository_manifest,
                "selected_tag": repository.status.selected_tag,
                "show_beta": repository.status.show_beta,
                "stars": repository.data.stargazers_count,
                "topics": repository.data.topics,
                "version_installed": repository.versions.installed,
            }

        await async_save_to_store(self.hacs.hass, "repositories", content)
        self.hacs.hass.bus.async_fire("hacs/repository", {})
        self.hacs.hass.bus.fire("hacs/config", {})

    async def restore(self):
        """Restore saved data."""
        hacs = await async_load_from_store(self.hacs.hass, "hacs")
        repositories = await async_load_from_store(self.hacs.hass, "repositories")
        removed = await async_load_from_store(self.hacs.hass, "removed")
        try:
            if not hacs and not repositories:
                # Assume new install
                self.hacs.system.status.new = True
                return True
            self.logger.info("Restore started")

            # Hacs
            self.hacs.configuration.frontend_mode = hacs.get("view", "Grid")
            self.hacs.configuration.frontend_compact = hacs.get("compact", False)
            self.hacs.configuration.onboarding_done = hacs.get("onboarding_done", False)

            for entry in removed:
                removed_repo = get_removed(entry["repository"])
                removed_repo.update_data(entry)

            # Repositories
            for entry in repositories:
                repo = repositories[entry]
                if not self.hacs.is_known(repo["full_name"]):
                    await register_repository(
                        repo["full_name"], repo["category"], False
                    )
                repository = self.hacs.get_by_name(repo["full_name"])
                if repository is None:
                    self.logger.error(f"Did not find {repo['full_name']}")
                    continue

                # Restore repository attributes
                repository.information.uid = entry
                await self.hacs.hass.async_add_executor_job(
                    restore_repository_data, repository, repo
                )

            self.logger.info("Restore done")
        except Exception as exception:  # pylint: disable=broad-except
            self.logger.critical(f"[{exception}] Restore Failed!")
            return False
        return True


def restore_repository_data(
    repository: type(HacsRepository), repository_data: dict
) -> None:
    """Restore Repository Data"""
    repository.data.authors = repository_data.get("authors", [])
    repository.data.description = repository_data.get("description")
    repository.releases.last_release_object_downloads = repository_data.get("downloads")
    repository.information.last_updated = repository_data.get("last_updated")
    repository.data.topics = repository_data.get("topics", [])
    repository.data.stargazers_count = repository_data.get("stars", 0)
    repository.releases.last_release = repository_data.get("last_release_tag")
    repository.status.hide = repository_data.get("hide", False)
    repository.status.installed = repository_data.get("installed", False)
    repository.status.new = repository_data.get("new", True)
    repository.status.selected_tag = repository_data.get("selected_tag")
    repository.status.show_beta = repository_data.get("show_beta", False)
    repository.versions.available = repository_data.get("last_release_tag")
    repository.versions.available_commit = repository_data.get("last_commit")
    repository.versions.installed = repository_data.get("version_installed")
    repository.versions.installed_commit = repository_data.get("installed_commit")

    repository.repository_manifest = HacsManifest.from_dict(
        repository_data.get("repository_manifest", {})
    )

    if repository.status.installed:
        repository.status.first_install = False

    if repository_data["full_name"] == "hacs/integration":
        repository.versions.installed = VERSION
        repository.status.installed = True
