#!/usr/bin/env python3
"""Patch downloaded HACS frontend bundles to use the local icon resolver."""

from __future__ import annotations

import gzip
import importlib.util
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = REPO_ROOT / "custom_components" / "hacs" / "utils" / "frontend_icon_patch.py"

spec = importlib.util.spec_from_file_location("frontend_icon_patch", HELPER_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Unable to load frontend icon patch helper from {HELPER_PATH}")

frontend_icon_patch = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = frontend_icon_patch
spec.loader.exec_module(frontend_icon_patch)

patch_dashboard_bundle = frontend_icon_patch.patch_dashboard_bundle


def _patch_directory(directory: Path, *, es5: bool) -> list[Path]:
    patched: list[Path] = []

    for bundle in sorted(directory.glob("*.js")):
        content = bundle.read_text(encoding="utf-8")
        try:
            updated = patch_dashboard_bundle(content, es5=es5)
        except ValueError:
            continue

        if updated != content:
            bundle.write_text(updated, encoding="utf-8")
            with gzip.open(bundle.with_suffix(f"{bundle.suffix}.gz"), "wt", encoding="utf-8") as handle:
                handle.write(updated)
        patched.append(bundle)

    if not patched:
        raise FileNotFoundError(f"No dashboard bundle was patched under {directory}")

    return patched


def main() -> int:
    """Patch both modern and ES5 dashboard bundles."""
    frontend_root = REPO_ROOT / "custom_components" / "hacs" / "hacs_frontend"

    latest = _patch_directory(frontend_root / "frontend_latest", es5=False)
    es5 = _patch_directory(frontend_root / "frontend_es5", es5=True)

    for bundle in [*latest, *es5]:
        print(f"Patched {bundle.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
