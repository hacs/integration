from hacs_frontend.version import VERSION as FE_VERSION
from hacs_frontend import locate_dir

from custom_components.hacs.helpers.functions.logger import getLogger
from custom_components.hacs.webresponses.frontend import HacsFrontendDev
from custom_components.hacs.helpers.functions.information import get_frontend_version
from custom_components.hacs.share import get_hacs

from ...enums import HacsSetupTask


URL_BASE = "/hacsfiles"


async def async_setup_frontend():
    """Configure the HACS frontend elements."""
    hacs = get_hacs()
    hacs.log.info("Setup task %s", HacsSetupTask.FRONTEND)
    hass = hacs.hass

    # Register themes
    hass.http.register_static_path(f"{URL_BASE}/themes", hass.config.path("themes"))

    # Register frontend
    if hacs.configuration.frontend_repo_url:
        getLogger().warning(
            "Frontend development mode enabled. Do not run in production."
        )
        hass.http.register_view(HacsFrontendDev())
    else:
        #
        hass.http.register_static_path(f"{URL_BASE}/frontend", locate_dir())

    # Custom iconset
    hass.http.register_static_path(
        f"{URL_BASE}/iconset.js", str(hacs.integration_dir / "iconset.js")
    )
    if "frontend_extra_module_url" not in hass.data:
        hass.data["frontend_extra_module_url"] = set()
    hass.data["frontend_extra_module_url"].add("/hacsfiles/iconset.js")

    # Register www/community for all other files
    hass.http.register_static_path(
        URL_BASE, hass.config.path("www/community"), cache_headers=False
    )

    hacs.frontend.version_running = FE_VERSION
    hacs.frontend.version_expected = await hass.async_add_executor_job(
        get_frontend_version
    )

    # Add to sidepanel
    if "hacs" not in hass.data.get("frontend_panels", {}):
        hass.components.frontend.async_register_built_in_panel(
            component_name="custom",
            sidebar_title=hacs.configuration.sidepanel_title,
            sidebar_icon=hacs.configuration.sidepanel_icon,
            frontend_url_path="hacs",
            config={
                "_panel_custom": {
                    "name": "hacs-frontend",
                    "embed_iframe": True,
                    "trust_external": False,
                    "js_url": "/hacsfiles/frontend/entrypoint.js",
                }
            },
            require_admin=True,
        )


async def async_serve_frontend(requested_file):
    hacs = get_hacs()
    requested = requested_file.split("/")[-1]
    servefile = None
    dev = False

    if hacs.configuration.frontend_repo_url or hacs.configuration.frontend_repo:
        dev = True

    if hacs.configuration.frontend_repo_url:
        _LOGGER.debug("Serving REMOTE DEVELOPMENT frontend")
        try:
            request = await hacs.session.get(
                f"{hacs.configuration.frontend_repo_url}/{requested}"
            )
            if request.status == 200:
                result = await request.read()
                response = web.Response(body=result)
                response.headers["Content-Type"] = "application/javascript"

                return response
        except (Exception, BaseException) as exception:
            _LOGGER.error(exception)

    elif hacs.configuration.frontend_repo:
        _LOGGER.debug("Serving LOCAL DEVELOPMENT frontend")
        servefile = f"{hacs.configuration.frontend_repo}/hacs_frontend/{requested}"
    else:
        servefile = f"{locate_dir()}/{requested}"

    if servefile is None or not await async_path_exsist(servefile):
        return web.Response(status=404)

    response = web.FileResponse(servefile)
    response.headers["Content-Type"] = "application/javascript"

    if dev:
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-store"
    return response
