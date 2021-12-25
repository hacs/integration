"""Helpers: Install: info_file."""
from custom_components.hacs.utils.information import info_file


def test_info_file(repository):
    assert not info_file(repository)

    repository.treefiles.append("info")
    assert info_file(repository) == "info"

    repository.treefiles = []
    repository.treefiles.append("INFO")
    assert info_file(repository) == "INFO"

    repository.treefiles = []
    repository.treefiles.append("info.md")
    assert info_file(repository) == "info.md"

    repository.treefiles = []
    repository.treefiles.append("INFO.MD")
    assert info_file(repository) == "INFO.MD"


def test_info_file_render_readme(repository):
    repository.data.render_readme = True
    repository.treefiles.append("info.md")
    assert not info_file(repository)

    repository.treefiles = []
    repository.treefiles.append("readme")
    assert info_file(repository) == "readme"

    repository.treefiles = []
    repository.treefiles.append("README")
    assert info_file(repository) == "README"

    repository.treefiles = []
    repository.treefiles.append("readme.md")
    assert info_file(repository) == "readme.md"

    repository.treefiles = []
    repository.treefiles.append("README.MD")
    assert info_file(repository) == "README.MD"
