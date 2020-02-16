# pylint: disable=invalid-name, missing-docstring

hacs = []


def get_hacs():
    if not hacs:
        from custom_components.hacs.hacsbase import Hacs

        hacs.append(Hacs())

    return hacs[0]

