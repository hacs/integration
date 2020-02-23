# pylint: disable=invalid-name, missing-docstring

hacs = []
removed_repositories = []


def get_hacs():
    if not hacs:
        from custom_components.hacs.hacsbase import Hacs

        hacs.append(Hacs())

    return hacs[0]

