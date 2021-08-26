"""Base class for repositories."""
from __future__ import annotations
from dataclasses import dataclass

from ..enums import HacsCategory
from ..mixin import HacsMixin, LogMixin


@dataclass
class HacsRepositoryBase(HacsMixin, LogMixin):
    """Base class for repositories."""

    repository_full_name: str
    category: HacsCategory

    repository_id: int | None = None
    repository_description: str | None = None
    repository_default_branch: str | None = None

    etag_repository: str | None = None

    @property
    def uses_releases(self) -> bool:
        """Boolean to indicate that the repository uses releases."""
        return False

    async def async_github_update_information(self) -> None:
        """Update repository information from github."""
        response = await self.hacs.githubapi.repos.get(
            self.repository_full_name, **{"etag": self.etag_repository}
        )

        if self.repository_full_name != response.data.full_name:
            self.hacs.common.renamed_repositories.setdefault(
                self.repository_full_name, response.data.full_name
            )

        ## Update hacs._repositories*
        for key in response.data.as_dict:
            if hasattr(self, f"repository_{key}"):
                self.__setattr__(f"repository_{key}", response.data.as_dict[key])
