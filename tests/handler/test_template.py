"""Template tests."""
# pylint: disable=missing-docstring
from custom_components.hacs.helpers.functions.template import render_template
from tests.dummy_repository import dummy_repository_base


class MockRelease:
    prerelease = True


def test_render_template(hass):
    repository = dummy_repository_base(hass)
    content = "ABC"
    render_template(content, repository)
    repository.releases.last_release_object = MockRelease()
    render_template(content, repository)
