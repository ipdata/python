import ipaddress
import os

import pytest
from dotenv import load_dotenv
from hypothesis import given, settings
from hypothesis import strategies as st

from pathlib import Path
import ipdata

# local testing
pwd = Path(__file__).parent.resolve()
load_dotenv(f"{pwd}/.env")

# Github CI runs
IPDATA_API_KEY = os.environ.get("IPDATA_API_KEY")
ipdata.api_key = IPDATA_API_KEY


@given(st.ip_addresses(network="8.8.8.0/24"))
@settings(deadline=None, max_examples=100)
@pytest.mark.api
def test_lookup_v4(ip):
    ip = str(ip)
    data = ipdata.lookup(ip)
    assert data.ip == ip


@given(st.ip_addresses(network="2620:11a:a000::/40"))
@settings(deadline=None, max_examples=100)
@pytest.mark.api
def test_lookup_v6(ip):
    ip = str(ip)
    data = ipdata.lookup(ip)

    # Capitalize to handle 2620:11A:A000::' == '2620:11a:a000::'
    assert data.ip.upper() == ip.upper()


@given(
    st.lists(st.ip_addresses(network="2620:11a:a000::/40"), min_size=1, max_size=100)
)
@settings(deadline=None, max_examples=100)
@pytest.mark.api
def test_bulk_v6(ips):
    ips = [str(ip) for ip in ips]
    data = ipdata.bulk(ips)

    # Check we got all results
    assert len(data.responses) == len(ips)

    # Capitalize to handle 2620:11A:A000::' == '2620:11a:a000::'
    for pair in zip(ips, [response.ip for response in data.responses]):
        assert pair[0].upper() == pair[0].upper()


@given(st.lists(st.ip_addresses(network="8.8.8.0/24"), min_size=1, max_size=100))
@settings(deadline=None, max_examples=100)
@pytest.mark.api
def test_bulk_v4(ips):
    ips = [str(ip) for ip in ips]
    data = ipdata.bulk(ips)

    # Check we got all results
    assert len(data.responses) == len(ips)

    for pair in zip(ips, [response.ip for response in data.responses]):
        assert pair[0] == pair[0]
