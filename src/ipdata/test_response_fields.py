"""
Offline tests for the response fields the API added in November 2026: the top-level booleans
'is_satellite' and 'is_anycast', which the API includes only when they are true, and the optional
'first_seen', 'last_seen' and 'days_seen' attributes of 'threat.blocklists' entries. The library passes
the JSON through unchanged. The fixtures are built from the specification samples; nothing here calls
the live API.
"""
import json

import httpx
import pytest

from ipdata.ipdata import IPData

# Sample A: satellite ISP. All other fields keep today's shape.
SATELLITE_RESPONSE = {
    "ip": "98.97.34.0",
    "is_satellite": True,
    "is_eu": False,
    "city": "Seattle",
    "country_code": "US",
    "asn": {
        "asn": "AS14593",
        "name": "Space Exploration Technologies Corporation",
        "domain": "spacex.com",
        "route": "98.97.32.0/21",
        "type": "business",
    },
    "threat": {
        "is_tor": False,
        "is_vpn": False,
        "is_icloud_relay": False,
        "is_proxy": False,
        "is_datacenter": False,
        "is_anonymous": False,
        "is_known_attacker": False,
        "is_known_abuser": False,
        "is_threat": False,
        "is_bogon": False,
        "blocklists": [],
        "scores": {"vpn_score": 0, "proxy_score": 1, "threat_score": 8, "trust_score": 97},
    },
    "count": "0",
}

# Sample B: anycast address with dated blocklist entries (complete response).
ANYCAST_RESPONSE = {
    "ip": "8.8.8.8",
    "is_anycast": True,
    "is_eu": False,
    "city": None,
    "region": None,
    "region_code": None,
    "region_type": None,
    "country_name": "United States",
    "country_code": "US",
    "continent_name": "North America",
    "continent_code": "NA",
    "latitude": 39.7599983215332,
    "longitude": -98.5,
    "postal": None,
    "calling_code": "1",
    "flag": "https://ipdata.co/flags/us.png",
    "emoji_flag": "\U0001F1FA\U0001F1F8",
    "emoji_unicode": "U+1F1FA U+1F1F8",
    "asn": {
        "asn": "AS15169",
        "name": "Google LLC",
        "domain": "about.google",
        "route": "8.8.8.0/24",
        "type": "hosting",
    },
    "company": {
        "name": "Google LLC",
        "domain": "about.google",
        "network": "8.8.8.0/24",
        "type": "hosting",
    },
    "languages": [{"name": "English", "native": "English", "code": "en"}],
    "currency": {
        "name": "US Dollar",
        "code": "USD",
        "symbol": "$",
        "native": "$",
        "plural": "US dollars",
    },
    "time_zone": {
        "name": None,
        "abbr": None,
        "offset": None,
        "is_dst": None,
        "current_time": None,
    },
    "threat": {
        "is_tor": False,
        "is_vpn": False,
        "is_icloud_relay": False,
        "is_proxy": False,
        "is_datacenter": True,
        "is_anonymous": False,
        "is_known_attacker": False,
        "is_known_abuser": False,
        "is_threat": False,
        "is_bogon": False,
        "blocklists": [
            {
                "days_seen": 1,
                "first_seen": "2026-11-02",
                "last_seen": "2026-11-02",
                "name": "ipdata",
                "site": "https://ipdata.co",
                "type": "cloud",
            },
            {
                "days_seen": 1,
                "first_seen": "2026-11-02",
                "last_seen": "2026-11-02",
                "name": "ipdata",
                "site": "https://ipdata.co",
                "type": "open_resolvers",
            },
        ],
        "scores": {"vpn_score": 100, "proxy_score": 93, "threat_score": 100, "trust_score": 2},
    },
    "count": "0",
}

# Sample C: VPN exit. Neither top-level flag is present and the third blocklist entry has no dates.
VPN_RESPONSE = {
    "ip": "187.13.250.1",
    "is_eu": False,
    "threat": {
        "is_tor": False,
        "is_vpn": True,
        "is_icloud_relay": False,
        "is_proxy": False,
        "is_datacenter": True,
        "is_anonymous": True,
        "is_known_attacker": True,
        "is_known_abuser": True,
        "is_threat": True,
        "is_bogon": False,
        "blocklists": [
            {
                "days_seen": 2,
                "first_seen": "2026-10-31",
                "last_seen": "2026-11-02",
                "name": "Gluetun",
                "site": "https://github.com/qdm12/gluetun",
                "type": "vpn",
            },
            {
                "days_seen": 1,
                "first_seen": "2026-11-02",
                "last_seen": "2026-11-02",
                "name": "ipdata",
                "site": "https://ipdata.co",
                "type": "cloud",
            },
            {"name": "ipdata", "site": "https://ipdata.co", "type": "vpn"},
            {
                "days_seen": 2,
                "first_seen": "2026-10-31",
                "last_seen": "2026-11-02",
                "name": "NordVPN",
                "site": "https://nordvpn.com",
                "type": "vpn",
            },
            {
                "days_seen": 2,
                "first_seen": "2026-10-31",
                "last_seen": "2026-11-02",
                "name": "Wikimedia Global Blocklist",
                "site": "https://wikimedia.org",
                "type": "general",
            },
            {
                "days_seen": 2,
                "first_seen": "2026-10-31",
                "last_seen": "2026-11-02",
                "name": "X4BNet",
                "site": "https://github.com/X4BNet/lists_vpn",
                "type": "vpn",
            },
        ],
        "scores": {"vpn_score": 100, "proxy_score": 99, "threat_score": 100, "trust_score": 0},
    },
    "count": "0",
}


def make_client(payload):
    """Returns an IPData client whose mock transport answers every request with 'payload', plus the requests."""
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=payload)

    return IPData("test", transport=httpx.MockTransport(handler)), requests


def test_is_satellite_is_passed_through_and_absent_flags_read_false():
    client, _ = make_client(SATELLITE_RESPONSE)

    data = client.lookup("98.97.34.0")

    assert data.is_satellite is True
    assert data["is_satellite"] is True
    assert data.is_eu is False
    # the API omits is_anycast when it is false; a missing key reads as None through dot notation
    assert "is_anycast" not in data
    assert data.is_anycast is None
    assert not data.is_anycast
    assert data.threat.blocklists == []
    assert data.threat.scores.trust_score == 97
    assert data.asn.name == "Space Exploration Technologies Corporation"
    assert data.status == 200


def test_is_anycast_with_dated_blocklist_entries():
    client, _ = make_client(ANYCAST_RESPONSE)

    data = client.lookup("8.8.8.8")

    assert data.is_anycast is True
    assert "is_satellite" not in data
    assert data.is_satellite is None
    assert data.threat.is_datacenter is True
    entries = data.threat.blocklists
    assert [entry.type for entry in entries] == ["cloud", "open_resolvers"]
    for entry in entries:
        assert entry.name == "ipdata"
        assert entry.site == "https://ipdata.co"
        # the dates stay plain YYYY-MM-DD strings; they are not parsed into date objects
        assert entry.first_seen == "2026-11-02"
        assert entry.last_seen == "2026-11-02"
        assert entry.days_seen == 1
    assert data.threat.scores.trust_score == 2
    assert data.time_zone.current_time is None
    assert data.city is None


def test_blocklist_entry_without_dates():
    client, _ = make_client(VPN_RESPONSE)

    data = client.lookup("187.13.250.1")

    assert "is_satellite" not in data
    assert "is_anycast" not in data
    assert data.threat.is_vpn is True
    entries = data.threat.blocklists
    assert len(entries) == 6
    undated = entries[2]
    assert undated.name == "ipdata"
    assert undated.type == "vpn"
    assert "first_seen" not in undated
    assert undated.first_seen is None
    assert undated.last_seen is None
    assert undated.days_seen is None
    assert entries[0].name == "Gluetun"
    assert entries[0].first_seen == "2026-10-31"
    assert entries[0].last_seen == "2026-11-02"
    assert [entry.get("days_seen") for entry in entries] == [2, 1, None, 2, 2, 2]


def test_bulk_items_carry_the_same_shape():
    client, requests = make_client([SATELLITE_RESPONSE, ANYCAST_RESPONSE, VPN_RESPONSE])

    data = client.bulk(["98.97.34.0", "8.8.8.8", "187.13.250.1"])

    assert requests[0].method == "POST"
    assert data.status == 200
    satellite, anycast, vpn = data.responses
    assert satellite.is_satellite is True
    assert satellite.is_anycast is None
    assert anycast.is_anycast is True
    assert anycast.is_satellite is None
    assert anycast.threat.blocklists[1].type == "open_resolvers"
    assert anycast.threat.blocklists[1].first_seen == "2026-11-02"
    assert vpn.is_satellite is None
    assert vpn.is_anycast is None
    assert vpn.threat.blocklists[2].first_seen is None
    assert vpn.threat.blocklists[3].days_seen == 2


def test_payload_passes_through_unchanged_and_tolerates_unknown_keys():
    payload = dict(ANYCAST_RESPONSE, brand_new_field={"nested": "value", "numbers": [1, 2, 3]})
    client, _ = make_client(payload)

    data = client.lookup("8.8.8.8")

    # DotDict is a plain dict; 'status' is the only key the library adds
    expected = dict(payload, status=200)
    assert dict(data) == expected
    assert json.loads(json.dumps(data)) == expected
    assert data.brand_new_field.nested == "value"
    assert data["brand_new_field"]["numbers"] == [1, 2, 3]


@pytest.mark.parametrize("field", ["is_satellite", "is_anycast"])
def test_new_field_names_are_accepted_for_field_selection(field):
    client, requests = make_client({"ip": "8.8.8.8", field: True})
    assert field in IPData.valid_fields
    client._validate_fields([field])
    client._validate_fields({field, "ip"})
    client._validate_fields((field,))

    data = client.lookup("8.8.8.8", fields=[field])
    assert requests[-1].url.params["fields"] == field
    assert data[field] is True

    client.lookup("8.8.8.8", select_field=field)
    assert requests[-1].url.params["fields"] == field


def test_both_new_fields_in_one_fields_list_for_lookup_and_bulk():
    client, requests = make_client([SATELLITE_RESPONSE])

    client.bulk(["98.97.34.0"], fields=["ip", "is_satellite", "is_anycast", "threat"])
    assert requests[-1].url.params["fields"] == "ip,is_satellite,is_anycast,threat"

    with pytest.raises(ValueError):
        client.lookup("98.97.34.0", fields=["is_satelite"])  # typo is still rejected
