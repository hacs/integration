""""Starting setup task: Frontend"."""
from __future__ import annotations

from typing import TYPE_CHECKING

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, URL_BASE
from .hacs_frontend import locate_dir, VERSION as FE_VERSION
from .hacs_frontend_experimental import (
    locate_dir as experimental_locate_dir,
    VERSION as EXPERIMENTAL_FE_VERSION,
)


if TYPE_CHECKING:
    from .base import HacsBase


@callback
def async_register_frontend(hass: HomeAssistant, hacs: HacsBase) -> None:
    """Register the frontend."""

    # Setup themes endpoint if needed
    hacs.async_setup_frontend_endpoint_themes()

    # Register frontend
    if hacs.configuration.frontend_repo_url:
        hacs.log.warning(
            "<HacsFrontend> Frontend development mode enabled. Do not run in production!"
        )
        hass.http.register_view(HacsFrontendDev())
    elif hacs.configuration.experimental:
        hacs.log.info("<HacsFrontend> Using experimental frontend")
        hass.http.register_static_path(
            f"{URL_BASE}/frontend", experimental_locate_dir(), cache_headers=False
        )
    else:
        #
        hass.http.register_static_path(f"{URL_BASE}/frontend", locate_dir(), cache_headers=False)

    # Custom iconset
    hass.http.register_static_path(
        f"{URL_BASE}/iconset.js", str(hacs.integration_dir / "iconset.js")
    )
    if "frontend_extra_module_url" not in hass.data:
        hass.data["frontend_extra_module_url"] = set()
    hass.data["frontend_extra_module_url"].add(f"{URL_BASE}/iconset.js")

    hacs.frontend_version = (
        FE_VERSION if not hacs.configuration.experimental else EXPERIMENTAL_FE_VERSION
    )

    # Add to sidepanel if needed
    if DOMAIN not in hass.data.get("frontend_panels", {}):
        hass.components.frontend.async_register_built_in_panel(
            component_name="custom",
            sidebar_title=hacs.configuration.sidepanel_title,
            sidebar_icon=hacs.configuration.sidepanel_icon,
            frontend_url_path=DOMAIN,
            config={
                "_panel_custom": {
                    "name": "hacs-frontend",
                    "embed_iframe": True,
                    "trust_external": False,
                    "js_url": f"/hacsfiles/frontend/entrypoint.js?hacstag={hacs.frontend_version}",
                }
            },
            require_admin=True,
        )

    # Setup plugin endpoint if needed
    hacs.async_setup_frontend_endpoint_plugin()


class HacsFrontendDev(HomeAssistantView):
    """Dev View Class for HACS."""

    requires_auth = False
    name = "hacs_files:frontend"
    url = r"/hacsfiles/frontend/{requested_file:.+}"

    async def get(self, request, requested_file):  # pylint: disable=unused-argument
        """Handle HACS Web requests."""
        hacs: HacsBase = request.app["hass"].data.get(DOMAIN)
        requested = requested_file.split("/")[-1]
        request = await hacs.session.get(f"{hacs.configuration.frontend_repo_url}/{requested}")
        if request.status == 200:
            result = await request.read()
            response = web.Response(body=result)
            response.headers["Content-Type"] = "application/javascript"

            return response
