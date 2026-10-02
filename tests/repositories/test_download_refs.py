"""Preserve tag and branch names when constructing downloads."""

from unittest.mock import AsyncMock

from aiogithubapi.models.release import GitHubReleaseModel
import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.exceptions import HacsException
from custom_components.hacs.repositories.base import HacsRepository


@pytest.mark.parametrize(
    ("ref", "default_branch", "force_branch", "expected_ref"),
    [
        ("tags/v1.0.0", "main", False, "v1.0.0"),
        ("tags/releases/tags/v1.0.0", "main", False, "releases/tags/v1.0.0"),
        ("tags/tags/v1.0.0", "main", False, "tags/v1.0.0"),
        ("fix-release-tags", "fix-release-tags", False, "fix-release-tags"),
        ("feature/tags/foo", "main", True, "feature/tags/foo"),
        ("tags/feature", "tags/feature", False, "tags/feature"),
        ("tags/feature", "main", True, "tags/feature"),
    ],
)
async def test_archive_download_preserves_ref(
    ref: str,
    default_branch: str,
    force_branch: bool,
    expected_ref: str,
) -> None:
    """Only strip an internal tag prefix before building archive URLs."""
    hacs = HacsBase()
    hacs.async_download_file = AsyncMock(return_value=None)
    repository = HacsRepository(hacs)
    repository.data.category = "integration"
    repository.data.full_name = "owner/repo"
    repository.data.default_branch = default_branch
    repository.force_branch = force_branch
    repository.ref = ref

    with pytest.raises(HacsException, match="Failed to download zipball"):
        await repository.download_repository_zip()

    assert [call.args[0] for call in hacs.async_download_file.call_args_list] == [
        f"https://github.com/owner/repo/archive/refs/tags/{expected_ref}.zip",
        f"https://github.com/owner/repo/archive/refs/heads/{expected_ref}.zip",
    ]


async def test_release_zip_preserves_tag_name() -> None:
    """Do not pass the internal tag prefix into release asset URLs."""
    repository = HacsRepository(HacsBase())
    repository.data.full_name = "owner/repo"
    repository.ref = "tags/releases/tags/v1.0.0"
    repository.repository_manifest.filename = "example.zip"
    repository.async_download_zip_file = AsyncMock()

    await repository.download_zip_files(repository.validate)

    content = repository.async_download_zip_file.call_args.args[0]
    assert content["url"] == (
        "https://github.com/owner/repo/releases/download/releases/tags/v1.0.0/example.zip"
    )


def test_release_assets_match_tag_name() -> None:
    """Match release assets even when the real tag contains tags/."""
    repository = HacsRepository(HacsBase())
    repository.data.category = "plugin"
    repository.data.releases = True
    repository.ref = "tags/releases/tags/v1.0.0"
    url = "https://github.com/owner/repo/releases/download/releases/tags/v1.0.0/example.js"
    repository.releases.objects = [
        GitHubReleaseModel(
            {
                "tag_name": "releases/tags/v1.0.0",
                "assets": [{"name": "example.js", "browser_download_url": url}],
            },
        ),
    ]

    assert [content.download_url for content in repository.gather_files_to_download()] == [url]
