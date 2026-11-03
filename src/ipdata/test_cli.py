"""
Offline tests for the command line interface. The IPData client that the commands create is replaced by one
wired to an httpx.MockTransport, so nothing here talks to the live API.
"""
import csv
import json

import httpx
import pytest
from click.testing import CliRunner

from ipdata import cli as cli_module
from ipdata.ipdata import IPData

ASN = {"asn": "AS15169", "name": "Google LLC", "domain": "about.google", "route": "8.8.8.0/24", "type": "hosting"}

# the members of the threat object, in the order the API returns them
THREAT = {
    "is_tor": False,
    "is_vpn": True,
    "is_icloud_relay": False,
    "is_proxy": False,
    "is_datacenter": False,
    "is_anonymous": True,
    "is_known_attacker": False,
    "is_known_abuser": False,
    "is_threat": False,
    "is_bogon": False,
    "blocklists": [
        {
            "name": "ipdata vpn",
            "site": "https://ipdata.co",
            "type": "vpn",
            "first_seen": "2026-10-31",
            "last_seen": "2026-11-02",
            "days_seen": 2,
        }
    ],
    "scores": {"vpn_score": 100, "proxy_score": 0, "threat_score": 0, "trust_score": 0},
}


def bulk_response(request):
    """Answers POST /bulk with one response per requested resource, in request order."""
    responses = [
        {"ip": ip, "country_code": "US", "asn": ASN, "threat": THREAT} for ip in json.loads(request.content)
    ]
    return httpx.Response(200, json=responses)


@pytest.fixture
def cli_requests(monkeypatch, tmp_path):
    """
    Points the CLI at a stored API key and makes it create clients that record their requests and answer them
    with bulk_response instead of sending them. Returns the list of recorded requests.
    """
    key_file = tmp_path / "api-key"
    key_file.write_text("test")
    monkeypatch.setattr(cli_module, "API_KEY_FILE", str(key_file))

    requests = []

    def handler(request):
        requests.append(request)
        return bulk_response(request)

    class RecordingIPData(IPData):
        def __init__(self, api_key=None, **kwargs):
            super().__init__(api_key, transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(cli_module, "IPData", RecordingIPData)
    return requests


def run_batch(tmp_path, *options, resources=("8.8.8.8", "1.1.1.1")):
    """Runs 'ipdata batch' on a file listing 'resources' and returns the click result and the output path."""
    source = tmp_path / "ips.txt"
    source.write_text("".join(f"{resource}\n" for resource in resources))
    output = tmp_path / "results"
    result = CliRunner().invoke(cli_module.cli, ["batch", str(source), "--output", str(output), *options])
    return result, output


def test_batch_exclude_requests_every_other_field(cli_requests, tmp_path):
    result, output = run_batch(tmp_path, "--exclude", "threat", "-e", "asn")

    assert result.exit_code == 0, result.output
    assert result.exception is None
    assert len(cli_requests) == 1
    requested = cli_requests[0].url.params["fields"].split(",")
    assert set(requested) == IPData.valid_fields - {"threat", "asn"}
    assert requested == sorted(requested)
    assert [json.loads(line)["ip"] for line in output.read_text().splitlines()] == ["8.8.8.8", "1.1.1.1"]


def test_batch_exclude_with_csv_output(cli_requests, tmp_path):
    result, output = run_batch(tmp_path, "--format", "CSV", "--exclude", "asn", "-e", "company")

    assert result.exit_code == 0, result.output
    reader = csv.DictReader(output.read_text().splitlines())
    rows = list(reader)
    assert len(rows) == 2
    assert not any(column.startswith(("asn_", "company_")) for column in reader.fieldnames)
    # the remaining fields are requested, and therefore written, in sorted order
    plain_columns = [column for column in reader.fieldnames if not column.startswith("threat_")]
    assert plain_columns == sorted(plain_columns)
    assert "ip" in plain_columns and "country_code" in plain_columns
    assert rows[0]["ip"] == "8.8.8.8"
    assert rows[0]["country_code"] == "US"
    assert rows[0]["threat_is_tor"] == "False"
    assert rows[1]["ip"] == "1.1.1.1"


def test_batch_rejects_fields_and_exclude_together(cli_requests, tmp_path):
    result, output = run_batch(tmp_path, "-f", "ip", "-e", "asn")

    assert result.exit_code != 0
    assert "mutually exclusive" in result.output
    assert cli_requests == []


def test_batch_csv_needs_fields_or_exclude(cli_requests, tmp_path):
    result, output = run_batch(tmp_path, "--format", "CSV")

    assert result.exit_code == 0
    assert cli_requests == []
    assert not output.exists()
