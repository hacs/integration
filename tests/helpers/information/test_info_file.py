"""Helpers: Install: info_file."""
from custom_components.hacs.helpers.functions.information import info_file

# pylint: disable=missing-docstring
from tests.dummy_repository import dummy_repository_base


def test_info_file(hass):
    repository = dummy_repository_base(hass)
    assert not info_file(repository)

    repository = dummy_repository_base(hass)
    repository.treefiles.append("info")
    assert info_file(repository) == "info"

    repository = dummy_repository_base(hass)
    repository.treefiles.append("INFO")
    assert info_file(repository) == "INFO"

    repository = dummy_repository_base(hass)
    repository.treefiles.append("info.md")
    assert info_file(repository) == "info.md"

    repository = dummy_repository_base(hass)
    repository.treefiles.append("INFO.MD")
    assert info_file(repository) == "INFO.MD"


def test_info_file_render_readme(hass):
    repository = dummy_repository_base(hass)
    repository.data.render_readme = True
    repository.treefiles.append("info.md")
    assert not info_file(repository)

    repository = dummy_repository_base(hass)
    repository.data.render_readme = True
    repository.treefiles.append("readme")
    assert info_file(repository) == "readme"

    repository = dummy_repository_base(hass)
    repository.data.render_readme = True
    repository.treefiles.append("README")
    assert info_file(repository) == "README"

    repository = dummy_repository_base(hass)
    repository.data.render_readme = True
    repository.treefiles.append("readme.md")
    assert info_file(repository) == "readme.md"

    repository = dummy_repository_base(hass)
    repository.data.render_readme = True
    repository.treefiles.append("README.MD")
    assert info_file(repository) == "README.MD"
