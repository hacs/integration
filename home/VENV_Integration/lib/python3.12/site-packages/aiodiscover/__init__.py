"""Top-level package for Async Host discovery."""

__author__ = "J. Nick Koston"
__email__ = "nick@koston.org"
# Do not edit this string manually, always use bumpversion
# Details in CONTRIBUTING.md
__version__ = "2.1.0"

from .discovery import DiscoverHosts  # noqa: F401


def get_module_version():
    return __version__
