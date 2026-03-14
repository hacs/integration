from custom_components.hacs.utils.frontend_icon_patch import (
    ES5_DASHBOARD_ICON_REPLACEMENT,
    ES5_DASHBOARD_ICON_SOURCE,
    LATEST_DASHBOARD_ICON_REPLACEMENT,
    LATEST_DASHBOARD_ICON_SOURCE,
    patch_dashboard_bundle,
)


def test_patch_dashboard_bundle_rewrites_latest_bundle():
    content = f"before {LATEST_DASHBOARD_ICON_SOURCE} after"

    assert patch_dashboard_bundle(content, es5=False) == (
        f"before {LATEST_DASHBOARD_ICON_REPLACEMENT} after"
    )


def test_patch_dashboard_bundle_rewrites_es5_bundle():
    content = f"before {ES5_DASHBOARD_ICON_SOURCE} after"

    assert patch_dashboard_bundle(content, es5=True) == (
        f"before {ES5_DASHBOARD_ICON_REPLACEMENT} after"
    )


def test_patch_dashboard_bundle_is_idempotent():
    content = f"before {LATEST_DASHBOARD_ICON_REPLACEMENT} after"

    assert patch_dashboard_bundle(content, es5=False) == content
