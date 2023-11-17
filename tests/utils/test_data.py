from custom_components.hacs.base import HacsBase
from custom_components.hacs.repositories.base import HacsManifest, HacsRepository
from custom_components.hacs.utils.data import HacsData
import pytest


@pytest.mark.asyncio
async def test_exclude_manifest_keys(hacs: HacsBase, repository: HacsRepository) -> None:
    data = HacsData(hacs)
    assert data.content == {}

    repository.repository_manifest = HacsManifest.from_dict(
        {
            "name": "test",
            "documentation": {"en": "README.md", "nb": "docs/README.nb.md"},
            "content_in_root": True,
            "filename": "my_super_awesome_thing.js",
            "country": ["NO", "SE", "DK"],
        }
    )

    data.async_store_repository_data(repository)
    assert data.content[repository.data.id]["repository_manifest"] == {
            "name": "test",
            "content_in_root": True,
            "filename": "my_super_awesome_thing.js",
            "country": ["NO", "SE", "DK"],
        }
