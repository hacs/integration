"""Helpers for patching downloaded HACS frontend bundles."""

from __future__ import annotations

LATEST_DASHBOARD_ICON_SOURCE = (
    '(0,p.X1)({domain:e.domain||"invalid",type:"icon",useFallback:!0,'
    "darkOptimized:this.hass.themes?.darkMode})"
)
LATEST_DASHBOARD_ICON_REPLACEMENT = (
    'this.hass.hassUrl(`/api/hacs/icon/${e.id}${this.hass.themes?.darkMode?'
    '"?dark=1":""}`)'
)
ES5_DASHBOARD_ICON_SOURCE = (
    '(0,v.X1)({domain:e.domain||"invalid",type:"icon",useFallback:!0,'
    "darkOptimized:null===(t=this.hass.themes)||void 0===t?void 0:t.darkMode})"
)
ES5_DASHBOARD_ICON_REPLACEMENT = (
    'this.hass.hassUrl(`/api/hacs/icon/${e.id}${(null===(t=this.hass.themes)||'
    'void 0===t?void 0:t.darkMode)?"?dark=1":""}`)'
)


def patch_dashboard_bundle(content: str, *, es5: bool) -> str:
    """Patch a HACS dashboard bundle to use the local icon resolver."""
    source = ES5_DASHBOARD_ICON_SOURCE if es5 else LATEST_DASHBOARD_ICON_SOURCE
    replacement = (
        ES5_DASHBOARD_ICON_REPLACEMENT if es5 else LATEST_DASHBOARD_ICON_REPLACEMENT
    )

    if replacement in content:
        return content

    if source not in content:
        raise ValueError("Could not find the HACS dashboard integration icon expression")

    return content.replace(source, replacement, 1)
