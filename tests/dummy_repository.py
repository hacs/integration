"""Create a dummy repository."""
# pylint: disable=missing-docstring
from custom_components.hacs.repositories.repository import HacsRepository
from integrationhelper import Logger


def dummy_repository_base():
    repository = HacsRepository()
    repository.logger = Logger("hacs.test.test")
    repository.information.name = "test"
    repository.information.full_name = "test/test"
    repository.information.default_branch = "master"
    repository.versions.available = "3"
    repository.status.selected_tag = "3"
    repository.releases.published_tags = ["1", "2", "3"]
    return repository
