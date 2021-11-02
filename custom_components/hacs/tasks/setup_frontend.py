""""Starting setup task: Frontend"."""
from __future__ import annotations

from hacs_frontend import locate_dir
from hacs_frontend.version import VERSION as FE_VERSION

from ..const import DOMAIN
from ..enums import HacsStage
from ..webresponses.frontend import HacsFrontendDev
from .base import HacsTask

URL_BASE = "/hacsfiles"


from homeassistant.core import HomeAssistant

from ..base import HacsBase


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """Setup the HACS frontend."""

    stages = [HacsStage.SETUP]

    async def async_execute(self) -> None:

        # Register themes
        self.hass.http.register_static_path(f"{URL_BASE}/themes", self.hass.config.path("themes"))

        # Register frontend
        if self.hacs.configuration.frontend_repo_url:
            self.log.warning("Frontend development mode enabled. Do not run in production!")
            self.hass.http.register_view(HacsFrontendDev())
        else:
            #
            self.hass.http.register_static_path(
                f"{URL_BASE}/frontend", locate_dir(), cache_headers=False
            )

        # Custom iconset
        self.hass.http.register_static_path(
            f"{URL_BASE}/iconset.js", str(self.hacs.integration_dir / "iconset.js")
        )
        if "frontend_extra_module_url" not in self.hass.data:
            self.hass.data["frontend_extra_module_url"] = set()
        self.hass.data["frontend_extra_module_url"].add(f"{URL_BASE}/iconset.js")

        # Register www/community for all other files
        use_cache = self.hacs.core.lovelace_mode == "storage"
        self.log.info(
            "%s mode, cache for /hacsfiles/: %s",
            self.hacs.core.lovelace_mode,
            use_cache,
        )
        self.hass.http.register_static_path(
            URL_BASE,
            self.hass.config.path("www/community"),
            cache_headers=use_cache,
        )

        self.hacs.frontend.version_running = FE_VERSION
        for requirement in self.hacs.integration.requirements:
            if "hacs_frontend" in requirement:
                self.hacs.frontend.version_expected = requirement.split("==")[-1]

        # Add to sidepanel if needed
        if DOMAIN not in self.hass.data.get("frontend_panels", {}):
            self.hass.components.frontend.async_register_built_in_panel(
                component_name="custom",
                sidebar_title=self.hacs.configuration.sidepanel_title,
                sidebar_icon=self.hacs.configuration.sidepanel_icon,
                frontend_url_path=DOMAIN,
                config={
                    "_panel_custom": {
                        "name": "hacs-frontend",
                        "embed_iframe": True,
                        "trust_external": False,
                        "js_url": f"/hacsfiles/frontend/entrypoint.js?hacstag={FE_VERSION}",
                    }
                },
                require_admin=True,
            )
