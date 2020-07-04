from aiohttp import web
from custom_components.hacs.share import get_hacs


def serve_iconset():
    hacs = get_hacs()
    return web.FileResponse(
        f"{hacs.system.config_path}/custom_components/hacs/iconset.js"
    )
