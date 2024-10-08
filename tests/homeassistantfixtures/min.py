"""Return a Home Assistant object pointing at test config dir.

This should be copied from the minimum supported version,
currently Home Assistant Core 2024.4.1.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import functools as ft
from unittest.mock import AsyncMock, Mock, patch

from homeassistant import auth, bootstrap, config_entries, loader
from homeassistant.auth import auth_store
from homeassistant.const import EVENT_HOMEASSISTANT_CLOSE, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers import (
    area_registry as ar,
    category_registry as cr,
    device_registry as dr,
    entity,
    entity_registry as er,
    floor_registry as fr,
    issue_registry as ir,
    label_registry as lr,
    restore_state as rs,
    translation,
)
import homeassistant.util.dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM

from .common import (
    INSTANCES,
    StoreWithoutWriteLoad,
    ensure_auth_manager_loaded,
    get_test_config_dir,
)


# pylint: disable=protected-access
@asynccontextmanager
async def async_test_home_assistant(
    event_loop: asyncio.AbstractEventLoop | None = None,
    load_registries: bool = True,
    config_dir: str | None = None,
) -> AsyncGenerator[HomeAssistant]:
    """Return a Home Assistant object pointing at test config dir.

    This should be copied from the minimum supported version,
    currently Home Assistant Core 2024.4.1.
    """
    hass = HomeAssistant(config_dir or get_test_config_dir())
    store = auth_store.AuthStore(hass)
    hass.auth = auth.AuthManager(hass, store, {}, {})
    ensure_auth_manager_loaded(hass.auth)
    INSTANCES.append(hass)

    orig_async_add_job = hass.async_add_job
    orig_async_add_executor_job = hass.async_add_executor_job
    orig_async_create_task = hass.async_create_task
    orig_tz = dt_util.DEFAULT_TIME_ZONE

    def async_add_job(target, *args, eager_start: bool = False):
        """Add job."""
        check_target = target
        while isinstance(check_target, ft.partial):
            check_target = check_target.func

        if isinstance(check_target, Mock) and not isinstance(target, AsyncMock):
            fut = asyncio.Future()
            fut.set_result(target(*args))
            return fut

        return orig_async_add_job(target, *args, eager_start=eager_start)

    def async_add_executor_job(target, *args):
        """Add executor job."""
        check_target = target
        while isinstance(check_target, ft.partial):
            check_target = check_target.func

        if isinstance(check_target, Mock):
            fut = asyncio.Future()
            fut.set_result(target(*args))
            return fut

        return orig_async_add_executor_job(target, *args)

    def async_create_task(coroutine, name=None, eager_start=False):
        """Create task."""
        if isinstance(coroutine, Mock) and not isinstance(coroutine, AsyncMock):
            fut = asyncio.Future()
            fut.set_result(None)
            return fut

        return orig_async_create_task(coroutine, name, eager_start)

    hass.async_add_job = async_add_job
    hass.async_add_executor_job = async_add_executor_job
    hass.async_create_task = async_create_task

    hass.data[loader.DATA_CUSTOM_COMPONENTS] = {}

    hass.config.location_name = "test home"
    hass.config.latitude = 32.87336
    hass.config.longitude = -117.22743
    hass.config.elevation = 0
    hass.config.set_time_zone("US/Pacific")
    hass.config.units = METRIC_SYSTEM
    hass.config.media_dirs = {"local": get_test_config_dir("media")}
    hass.config.skip_pip = True
    hass.config.skip_pip_packages = []

    hass.config_entries = config_entries.ConfigEntries(
        hass,
        {"_": ("Not empty or else some bad checks for hass config in discovery.py breaks")},
    )
    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP,
        hass.config_entries._async_shutdown,
        run_immediately=True,
    )

    # Load the registries
    entity.async_setup(hass)
    loader.async_setup(hass)

    # setup translation cache instead of calling translation.async_setup(hass)
    hass.data[translation.TRANSLATION_FLATTEN_CACHE] = translation._TranslationCache(hass)
    if load_registries:
        with (
            patch.object(StoreWithoutWriteLoad, "async_load", return_value=None),
            patch(
                "homeassistant.helpers.area_registry.AreaRegistryStore",
                StoreWithoutWriteLoad,
            ),
            patch(
                "homeassistant.helpers.device_registry.DeviceRegistryStore",
                StoreWithoutWriteLoad,
            ),
            patch(
                "homeassistant.helpers.entity_registry.EntityRegistryStore",
                StoreWithoutWriteLoad,
            ),
            patch(
                "homeassistant.helpers.storage.Store",  # Floor & label registry are different
                StoreWithoutWriteLoad,
            ),
            patch(
                "homeassistant.helpers.issue_registry.IssueRegistryStore",
                StoreWithoutWriteLoad,
            ),
            patch(
                "homeassistant.helpers.restore_state.RestoreStateData.async_setup_dump",
                return_value=None,
            ),
            patch(
                "homeassistant.helpers.restore_state.start.async_at_start",
            ),
        ):
            await ar.async_load(hass)
            await cr.async_load(hass)
            await dr.async_load(hass)
            await er.async_load(hass)
            await fr.async_load(hass)
            await ir.async_load(hass)
            await lr.async_load(hass)
            await rs.async_load(hass)
        hass.data[bootstrap.DATA_REGISTRIES_LOADED] = None

    hass.set_state(CoreState.running)

    @callback
    def clear_instance(event):
        """Clear global instance."""
        INSTANCES.remove(hass)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_CLOSE, clear_instance)

    yield hass

    # Restore timezone, it is set when creating the hass object
    dt_util.DEFAULT_TIME_ZONE = orig_tz
