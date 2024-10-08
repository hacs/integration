from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TypeVar

from homeassistant import core as ha
from homeassistant.helpers import storage

INSTANCES = []
_T = TypeVar("_T", bound=Mapping[str, Any] | Sequence[Any])


def get_test_config_dir(*add_path):
    """Return a path to a test config dir."""
    return Path(Path(__file__).resolve().parent, "testing_config", *add_path)


@ha.callback
def ensure_auth_manager_loaded(auth_mgr):
    """Ensure an auth manager is considered loaded."""
    store = auth_mgr._store
    if store._users is None:
        store._set_defaults()


class StoreWithoutWriteLoad(storage.Store[_T]):
    """Fake store that does not write or load. Used for testing."""

    async def async_save(self, *args: Any, **kwargs: Any) -> None:
        """Save the data.

        This function is mocked out in tests.
        """

    @ha.callback
    def async_save_delay(self, *args: Any, **kwargs: Any) -> None:
        """Save data with an optional delay.

        This function is mocked out in tests.
        """
