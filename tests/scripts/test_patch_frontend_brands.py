from __future__ import annotations

import gzip
import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "patch_frontend_brands.py"
SPEC = importlib.util.spec_from_file_location("patch_frontend_brands", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_make_replacement_routes_fallback_icons_to_local_domain_api():
    replacement = MODULE.make_replacement("brandsUrl", "icon")

    assert replacement == (
        "const brandsUrl=icon=>"
        'icon.useFallback?`/api/hacs/icon/domain/${icon.domain}${icon.darkOptimized?'
        '"?dark=1":""}`:'
        '`https://brands.home-assistant.io/${icon.brand?"brands/":""}${icon.domain}/'
        '${icon.darkOptimized?"dark_":""}${icon.type}.png`'
    )


def test_patch_file_updates_bundle_and_gzip(tmp_path: Path):
    content = (
        'const brandsUrl=icon=>`https://brands.home-assistant.io/'
        '${icon.brand?"brands/":""}${icon.useFallback?"_/":""}${icon.domain}/'
        '${icon.darkOptimized?"dark_":""}${icon.type}.png`'
    )
    bundle = tmp_path / "chunk.js"
    bundle.write_text(content, encoding="utf-8")
    with gzip.open(tmp_path / "chunk.js.gz", "wt", encoding="utf-8") as handle:
        handle.write(content)

    assert MODULE.patch_file(bundle) is True
    assert "/api/hacs/icon/domain/${icon.domain}" in bundle.read_text(encoding="utf-8")
    with gzip.open(tmp_path / "chunk.js.gz", "rt", encoding="utf-8") as handle:
        assert "/api/hacs/icon/domain/${icon.domain}" in handle.read()
