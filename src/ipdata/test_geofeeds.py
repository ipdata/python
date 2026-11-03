import httpx
import pytest

from .geofeeds import Entry, Geofeed, GeofeedValidationError


@pytest.mark.parametrize(
    "entry",
    [
        "172.32.0.0/55,,,,",
        "172.32.0.0/11,,,,",
        "172.32.0.0/11,ZZ,,,",
        "172.32.0.0/11,US,ZZ-ZZ,,",
        "172.32.0.0/11,US,LU-LU,,",
    ],
)
@pytest.mark.geofeed
def test_validation_rules(entry):
    entry = Entry(*entry.split(","))
    with pytest.raises(GeofeedValidationError):
        entry.validate()


@pytest.mark.geofeed
def test_download_follows_redirects(monkeypatch, tmp_path):
    from . import geofeeds

    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(
            200, text="# comment line\n8.8.8.0/24,US,US-CA,Mountain View,94043\n"
        )

    monkeypatch.setattr(geofeeds.httpx, "get", fake_get)
    feed = Geofeed("https://example.com/geofeed.csv", dir=str(tmp_path))

    entries = list(feed)

    assert calls == [("https://example.com/geofeed.csv", {"timeout": 60, "follow_redirects": True})]
    assert feed.cache_path.startswith(str(tmp_path))
    assert len(entries) == 1
    assert entries[0].ip_range == "8.8.8.0/24"
    assert entries[0].country == "US"
    entries[0].validate()
