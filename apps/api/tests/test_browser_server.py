"""The generated-artwork browser fixture must remain explicitly test-only."""
import io
from pathlib import Path
import runpy

from PIL import Image
import pytest
import uvicorn

from relicrat.barcode_errors import LookupUnavailable
from relicrat.barcode_providers import PROVIDERS

BOOTSTRAP = Path(__file__).with_name("browser_server.py")


def test_browser_bootstrap_requires_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("RELICRAT_SYNTHETIC_SMOKE", raising=False)
    with pytest.raises(SystemExit, match="explicit test API"):
        runpy.run_path(str(BOOTSTRAP))


def test_browser_bootstrap_refuses_non_test_database(monkeypatch):
    monkeypatch.setenv("RELICRAT_SYNTHETIC_SMOKE", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://db/inventory")
    with pytest.raises(SystemExit, match="disposable _test database"):
        runpy.run_path(str(BOOTSTRAP))


def test_browser_cover_fixture_is_bounded_and_keeps_real_api(monkeypatch):
    monkeypatch.setenv("RELICRAT_SYNTHETIC_SMOKE", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://db/browser_test")
    monkeypatch.setitem(PROVIDERS["musicbrainz"], "cover", PROVIDERS["musicbrainz"]["cover"])
    starts = []
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: starts.append((args, kwargs)))
    runpy.run_path(str(BOOTSTRAP))
    assert starts == [(("relicrat.main:app",), {"host": "0.0.0.0", "port": 8000})]
    cover = PROVIDERS["musicbrainz"]["cover"]
    with Image.open(io.BytesIO(cover("11111111-1111-4111-8111-111111111111"))) as image:
        assert image.format == "JPEG"
        assert image.size == (8, 8)
    with pytest.raises(LookupUnavailable):
        cover("22222222-2222-4222-8222-222222222222")
