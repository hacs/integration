"""Data handler for HACS."""
from integrationhelper import Logger
from ..const import VERSION
from ..repositories.repository import HacsRepository
from ..repositories.manifest import HacsManifest
from ..store import async_save_to_store, async_load_from_store

from custom_components.hacs.globals import get_hacs
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

        # Repositories
        content = {}
        for repository in self.hacs.repositories:
            if repository.repository_manifest is not None:
                repository_manifest = repository.repository_manifest.manifest
            else:
                repository_manifest = None
            data = {
                "authors": repository.data.authors,
                "category": repository.data.category,
                "description": repository.data.description,
                "domain": repository.data.domain,
                "downloads": repository.data.downloads,
                "full_name": repository.data.full_name,
                "first_install": repository.status.first_install,
                "installed_commit": repository.data.installed_commit,
                "installed": repository.data.installed,
                "last_commit": repository.data.last_commit,
                "last_release_tag": repository.data.last_version,
                "last_updated": repository.data.last_updated,
                "name": repository.data.name,
                "new": repository.data.new,
                "repository_manifest": repository_manifest,
                "selected_tag": repository.data.selected_tag,
                "show_beta": repository.data.show_beta,
                "stars": repository.data.stargazers_count,
                "topics": repository.data.topics,
                "version_installed": repository.data.installed_version,
            }
            if data:
                if repository.data.installed and (
                    repository.data.installed_commit
                    or repository.data.installed_version
                ):
                    await async_save_to_store(
                        self.hacs.hass,
                        f"hacs/{repository.data.id}.hacs",
                        repository.data.to_json(),
                    )
                content[str(repository.data.id)] = data

        await async_save_to_store(self.hacs.hass, "repositories", content)
        self.hacs.hass.bus.async_fire("hacs/repository", {})
        self.hacs.hass.bus.fire("hacs/config", {})

    async def restore(self):
        """Restore saved data."""
        hacs = await async_load_from_store(self.hacs.hass, "hacs")
        repositories = await async_load_from_store(self.hacs.hass, "repositories")
        try:
            if not hacs and not repositories:
                # Assume new install
                self.hacs.system.status.new = True
                return True
            self.logger.info("Restore started")
            self.hacs.system.status.new = False

            # Hacs
            self.hacs.configuration.frontend_mode = hacs.get("view", "Grid")
            self.hacs.configuration.frontend_compact = hacs.get("compact", False)
            self.hacs.configuration.onboarding_done = hacs.get("onboarding_done", False)

            # Repositories
            for entry in repositories:
                repo = repositories[entry]
                if not self.hacs.is_known(entry):
                    await register_repository(
                        repo["full_name"], repo["category"], False
                    )
                repository = [
                    x
                    for x in self.hacs.repositories
                    if str(x.data.id) == str(entry)
                    or x.data.full_name == repo["full_name"]
                ]
                if not repository:
                    self.logger.error(f"Did not find {repo['full_name']} ({entry})")
                    continue

                repository = repository[0]

                # Restore repository attributes
                repository.data.id = entry
                await self.hacs.hass.async_add_executor_job(
                    restore_repository_data, repository, repo
                )

                restored = await async_load_from_store(
                    self.hacs.hass, f"hacs/{entry}.hacs"
                )

                if restored:
                    repository.data.update_data(restored)
                    if not repository.data.installed:
                        repository.logger.debug(
                            "Should be installed but is not... Fixing that!"
                        )
                        repository.data.installed = True

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
    repository.data.last_updated = repository_data.get("last_updated")
    repository.data.topics = repository_data.get("topics", [])
    repository.data.domain = repository_data.get("domain", None)
    repository.data.stargazers_count = repository_data.get("stars", 0)
    repository.releases.last_release = repository_data.get("last_release_tag")
    repository.data.hide = repository_data.get("hide", False)
    repository.data.installed = repository_data.get("installed", False)
    repository.data.new = repository_data.get("new", True)
    repository.data.selected_tag = repository_data.get("selected_tag")
    repository.data.show_beta = repository_data.get("show_beta", False)
    repository.data.last_version = repository_data.get("last_release_tag")
    repository.data.last_commit = repository_data.get("last_commit")
    repository.data.installed_version = repository_data.get("version_installed")
    repository.data.installed_commit = repository_data.get("installed_commit")

    repository.repository_manifest = HacsManifest.from_dict(
        repository_data.get("repository_manifest", {})
    )

    if repository.data.installed:
        repository.status.first_install = False

    if repository_data["full_name"] == "hacs/integration":
        repository.data.installed_version = VERSION
        repository.data.installed = True
