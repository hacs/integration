from aiohttp import web
from hacs_frontend import locate_dir

from custom_components.hacs.helpers.functions.logger import getLogger
from custom_components.hacs.helpers.functions.path_exsist import async_path_exsist
from custom_components.hacs.share import get_hacs

_LOGGER = getLogger()


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
