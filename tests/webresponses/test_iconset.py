from custom_components.hacs.webresponses.iconset import ICON, serve_iconset


def test_list_removed_repositories():
    response = serve_iconset()
    assert response.body._value.decode("utf-8") == ICON
