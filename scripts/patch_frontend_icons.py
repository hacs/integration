#!/usr/bin/env python3
"""Patch downloaded HACS frontend bundles for the repo-id icon API."""

from __future__ import annotations

import gzip
import re
import sys
from pathlib import Path

HELPER_PATTERN = re.compile(
    r'const (?P<func>[A-Za-z_$][\w$]*)=(?P<param>[A-Za-z_$][\w$]*)=>'
    r'(?P=param)\.useFallback\?`/api/hacs/icon/domain/\$\{(?P=param)\.domain\}'
    r'\$\{(?P=param)\.darkOptimized\?"\?dark=1":""\}`:`https://brands\.home-assistant\.io/'
    r'\$\{(?P=param)\.brand\?"brands/":""\}'
    r'\$\{(?P=param)\.domain\}/'
    r'\$\{(?P=param)\.darkOptimized\?"dark_":""\}'
    r'\$\{(?P=param)\.type\}\.png`'
)

MODERN_DASHBOARD_CALL = (
    '(0,p.X1)({domain:e.domain||"invalid",type:"icon",useFallback:!0,'
    'darkOptimized:this.hass.themes?.darkMode})'
)
MODERN_DASHBOARD_REPLACEMENT = (
    '`/api/hacs/icon/${e.id}${this.hass.themes?.darkMode?"?dark=1":""}`'
)

ES5_DASHBOARD_CALL = (
    '(0,v.X1)({domain:e.domain||"invalid",type:"icon",useFallback:!0,'
    'darkOptimized:null===(t=this.hass.themes)||void 0===t?void 0:t.darkMode})'
)
ES5_DASHBOARD_REPLACEMENT = (
    '"/api/hacs/icon/".concat('
    'e.id,(null===(t=this.hass.themes)||void 0===t?void 0:t.darkMode)?"?dark=1":"")'
)


def _restore_brands_helper(match: re.Match[str]) -> str:
    func = match.group("func")
    param = match.group("param")
    return (
        f"const {func}={param}=>`https://brands.home-assistant.io/"
        f'${{{param}.brand?"brands/":""}}'
        f'${{{param}.useFallback?"_/":""}}'
        f'${{{param}.domain}}/'
        f'${{{param}.darkOptimized?"dark_":""}}'
        f'${{{param}.type}}.png`'
    )


def patch_file(path: Path) -> bool:
    """Patch a frontend bundle in place."""
    content = path.read_text(encoding="utf-8")
    updated = HELPER_PATTERN.sub(_restore_brands_helper, content)
    updated = updated.replace(MODERN_DASHBOARD_CALL, MODERN_DASHBOARD_REPLACEMENT)
    updated = updated.replace(ES5_DASHBOARD_CALL, ES5_DASHBOARD_REPLACEMENT)

    if updated == content:
        return False

    path.write_text(updated, encoding="utf-8")

    gz_path = path.with_name(path.name + ".gz")
    if gz_path.exists():
        with gzip.open(gz_path, "wt", encoding="utf-8") as handle:
            handle.write(updated)

    return True


def main() -> int:
    """Patch all bundles under the given frontend root."""
    root = Path(sys.argv[1])
    count = 0
    for js in sorted(root.rglob("*.js")):
        if ".js." in js.name:
            continue
        if patch_file(js):
            count += 1
            print(f"Patched: {js.relative_to(root)}")

    print(f"\nTotal: {count} files patched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
