"""Helpers: Install: info_file."""
# pylint: disable=missing-docstring
from tests.dummy_repository import dummy_repository_base
from custom_components.hacs.helpers.information import info_file


def test_info_file():
    repository = dummy_repository_base()
    assert not info_file(repository)

    repository = dummy_repository_base()
    repository.treefiles.append("info")
    assert info_file(repository) == "info"

    repository = dummy_repository_base()
    repository.treefiles.append("INFO")
    assert info_file(repository) == "INFO"

    repository = dummy_repository_base()
    repository.treefiles.append("info.md")
    assert info_file(repository) == "info.md"

    repository = dummy_repository_base()
    repository.treefiles.append("INFO.MD")
    assert info_file(repository) == "INFO.MD"

    repository = dummy_repository_base()
    repository.data.render_readme = True
    repository.treefiles.append("info.md")
    assert not info_file(repository)

    repository = dummy_repository_base()
    repository.data.render_readme = True
    repository.treefiles.append("readme")
    assert info_file(repository) == "readme"

    repository = dummy_repository_base()
    repository.data.render_readme = True
    repository.treefiles.append("README")
    assert info_file(repository) == "README"

    repository = dummy_repository_base()
    repository.data.render_readme = True
    repository.treefiles.append("readme.md")
    assert info_file(repository) == "readme.md"

    repository = dummy_repository_base()
    repository.data.render_readme = True
    repository.treefiles.append("README.MD")
    assert info_file(repository) == "README.MD"
