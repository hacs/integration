from __future__ import annotations

import gzip
import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "patch_frontend_icons.py"
SPEC = importlib.util.spec_from_file_location("patch_frontend_icons", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_restore_brands_helper_keeps_fallback_on_brands_cdn():
    match = MODULE.HELPER_PATTERN.search(  # noqa: SLF001
        'const brandsUrl=icon=>'
        'icon.useFallback?`/api/hacs/icon/domain/${icon.domain}${icon.darkOptimized?'
        '"?dark=1":""}`:'
        '`https://brands.home-assistant.io/${icon.brand?"brands/":""}${icon.domain}/'
        '${icon.darkOptimized?"dark_":""}${icon.type}.png`'
    )
    assert match is not None
    replacement = MODULE._restore_brands_helper(match)  # noqa: SLF001

    assert replacement == (
        'const brandsUrl=icon=>'
        '`https://brands.home-assistant.io/${icon.brand?"brands/":""}'
        '${icon.useFallback?"_/":""}${icon.domain}/'
        '${icon.darkOptimized?"dark_":""}${icon.type}.png`'
    )


def test_patch_file_updates_helper_dashboard_and_gzip(tmp_path: Path):
    content = (
        'const brandsUrl=icon=>'
        'icon.useFallback?`/api/hacs/icon/domain/${icon.domain}${icon.darkOptimized?'
        '"?dark=1":""}`:'
        '`https://brands.home-assistant.io/${icon.brand?"brands/":""}${icon.domain}/'
        '${icon.darkOptimized?"dark_":""}${icon.type}.png`'
        'template:e=>"integration"===e.category?n.dy` <img src="${'
        '(0,p.X1)({domain:e.domain||"invalid",type:"icon",useFallback:!0,'
        'darkOptimized:this.hass.themes?.darkMode})}" /> `:null'
    )
    bundle = tmp_path / "chunk.js"
    bundle.write_text(content, encoding="utf-8")
    with gzip.open(tmp_path / "chunk.js.gz", "wt", encoding="utf-8") as handle:
        handle.write(content)

    assert MODULE.patch_file(bundle) is True

    updated = bundle.read_text(encoding="utf-8")
    assert 'https://brands.home-assistant.io/${icon.brand?"brands/":""}${icon.useFallback?"_/":""}${icon.domain}/' in updated
    assert '/api/hacs/icon/${e.id}${this.hass.themes?.darkMode?"?dark=1":""}' in updated
    with gzip.open(tmp_path / "chunk.js.gz", "rt", encoding="utf-8") as handle:
        gz_updated = handle.read()
    assert updated == gz_updated
