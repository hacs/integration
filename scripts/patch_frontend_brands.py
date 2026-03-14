#!/usr/bin/env python3
"""Patch all HACS frontend bundles to route fallback brand icons through the local resolver."""

from __future__ import annotations

import gzip
import re
import sys
from pathlib import Path

# The helper is minified, but the identifier names can still vary between chunks.
# Pattern: const brandsUrl=icon=>`https://brands.home-assistant.io/...${icon.prop}...`
PATTERN = re.compile(
    r'const (?P<func>[A-Za-z_$][\w$]*)=(?P<param>[A-Za-z_$][\w$]*)=>'
    r'`https://brands\.home-assistant\.io/'
    r'\$\{(?P=param)\.brand\?"brands/":[^}]+\}'
    r'\$\{(?P=param)\.useFallback\?"_/":[^}]+\}'
    r'\$\{(?P=param)\.domain\}/'
    r'\$\{(?P=param)\.darkOptimized\?"dark_":[^}]+\}'
    r'\$\{(?P=param)\.type\}\.png`'
)


def make_replacement(func_name: str, param: str) -> str:
    """Build the replacement string for given function and parameter names."""
    return (
        f"const {func_name}={param}=>"
        f'{param}.useFallback?`/api/hacs/icon/domain/${{{param}.domain}}'
        f'${{{param}.darkOptimized?"?dark=1":""}}`'
        f":`https://brands.home-assistant.io/"
        f'${{{param}.brand?"brands/":""}}'
        f'${{{param}.domain}}/'
        f'${{{param}.darkOptimized?"dark_":""}}'
        f'${{{param}.type}}.png`'
    )


def _replacer(match: re.Match) -> str:
    return make_replacement(match.group("func"), match.group("param"))


def patch_file(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    if not PATTERN.search(content):
        return False
    updated = PATTERN.sub(_replacer, content)
    path.write_text(updated, encoding="utf-8")
    gz = path.parent / (path.name + ".gz")
    if gz.exists():
        with gzip.open(gz, "wt", encoding="utf-8") as f:
            f.write(updated)
    return True


def main() -> int:
    root = Path(sys.argv[1])
    count = 0
    for js in sorted(root.rglob("*.js")):
        if ".js." in js.name:
            continue
        if patch_file(js):
            count += 1
            print(f"Patched: {js.relative_to(root)}")
    print(f"\nTotal: {count} files patched")
    return 0 if count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
