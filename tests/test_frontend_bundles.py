from __future__ import annotations

import gzip
from pathlib import Path


FRONTEND_ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "hacs" / "hacs_frontend"
LATEST_DASHBOARD = FRONTEND_ROOT / "frontend_latest" / "9452.612b016de13c47d8.js"
ES5_DASHBOARD = FRONTEND_ROOT / "frontend_es5" / "9452.545f7feca8221863.js"


def test_dashboard_bundle_uses_repository_id_icon_api():
    latest = LATEST_DASHBOARD.read_text(encoding="utf-8")
    assert '/api/hacs/icon/${e.id}${this.hass.themes?.darkMode?"?dark=1":""}' in latest

    es5 = ES5_DASHBOARD.read_text(encoding="utf-8")
    assert '"/api/hacs/icon/".concat(e.id,' in es5
    assert '"?dark=1"' in es5


def test_vendored_frontend_no_longer_uses_domain_icon_api():
    for bundle in FRONTEND_ROOT.rglob("*.js"):
        assert "/api/hacs/icon/domain/" not in bundle.read_text(encoding="utf-8")

    for bundle in FRONTEND_ROOT.rglob("*.js.gz"):
        with gzip.open(bundle, "rt", encoding="utf-8") as handle:
            assert "/api/hacs/icon/domain/" not in handle.read()
