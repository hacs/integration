"""Template tests."""
# pylint: disable=missing-docstring
from custom_components.hacs.helpers.functions.template import render_template


class MockRelease:
    prerelease = True


def test_render_template(repository):
    content = "ABC"
    render_template(content, repository)
    repository.releases.last_release_object = MockRelease()
    render_template(content, repository)
