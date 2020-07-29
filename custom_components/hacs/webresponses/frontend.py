from aiohttp import web
from hacs_frontend import locate_debug_gz, locate_gz

from custom_components.hacs.helpers.functions.logger import getLogger
from custom_components.hacs.helpers.functions.path_exsist import async_path_exsist
from custom_components.hacs.share import get_hacs

logger = getLogger("web.frontend")


async def async_serve_frontend():
    hacs = get_hacs()
    servefile = None
    dev = False

    if hacs.configuration.frontend_repo_url:
        dev = True
    elif hacs.configuration.frontend_repo:
        dev = True

    if hacs.configuration.debug:
        logger.debug("Serving DEBUG frontend")
        servefile = locate_debug_gz()

    elif hacs.configuration.frontend_repo_url:
        logger.debug("Serving REMOTE DEVELOPMENT frontend")
        try:
            request = await hacs.session.get(
                f"{hacs.configuration.frontend_repo_url}/main.js"
            )
            if request.status == 200:
                result = await request.read()
                response = web.Response(body=result)

                return response
        except (Exception, BaseException) as exception:
            logger.error(exception)

    elif hacs.configuration.frontend_repo:
        logger.debug("Serving LOCAL DEVELOPMENT frontend")
        servefile = f"{hacs.configuration.frontend_repo}/hacs_frontend/main.js"
    else:
        servefile = locate_gz()

    if servefile is None or not await async_path_exsist(servefile):
        return web.Response(status=404)

    response = web.FileResponse(servefile)

    if dev:
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-store"
    return response
