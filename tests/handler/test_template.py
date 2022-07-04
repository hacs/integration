"""Template tests."""
# pylint: disable=missing-docstring


from custom_components.hacs.utils.template import render_template


class MockRelease:
    prerelease = True


def test_render_template(hacs, repository):
    content = "ABC"
    render_template(hacs, content, repository)
    repository.releases.last_release_object = MockRelease()
    render_template(hacs, content, repository)

    assert render_template(hacs, "{{test.test}}", repository) == "{{test.test}}"
    assert render_template(hacs, "{%if True%}hi{%endif%}", repository) == "hi"

    hacs.configuration.experimental = True
    assert render_template(hacs, "{%if True%}hi{%endif%}", repository) == "{%if True%}hi{%endif%}"
