"""
Offline tests for the IPData client. Every request goes through an httpx.MockTransport injected with
'transport=', so nothing here talks to the live API.
"""
import json
import re
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
import pytest

import ipdata
from ipdata import ipdata as ipdata_module
from ipdata.ipdata import DotDict, IPData, IPDataException

LOOKUP_RESPONSE = {
    "ip": "8.8.8.8",
    "is_eu": False,
    "country_code": "US",
    "asn": {
        "asn": "AS15169",
        "name": "Google LLC",
        "domain": "about.google",
        "route": "8.8.8.0/24",
        "type": "hosting",
    },
    "count": "0",
}


class Recorder:
    """
    A MockTransport handler that records every request it receives and replays scripted responses in
    order. The last response repeats; an exception in the script is raised instead of being returned.
    """

    def __init__(self, *responses):
        self.requests = []
        self.responses = list(responses) or [httpx.Response(200, json=LOOKUP_RESPONSE)]

    def __call__(self, request):
        self.requests.append(request)
        response = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(response, Exception):
            raise response
        return response


def make_client(*responses, **kwargs):
    """Returns an IPData client wired to a recording mock transport, plus the recorder."""
    recorder = Recorder(*responses)
    kwargs.setdefault("api_key", "test")
    return IPData(transport=httpx.MockTransport(recorder), **kwargs), recorder


@pytest.fixture
def sleeps(monkeypatch):
    """Replaces the retry sleep with a recorder so that the retry schedule can be asserted instantly."""
    recorded = []
    monkeypatch.setattr(ipdata_module, "_sleep", recorded.append)
    return recorded


def test_lookup_sends_api_key_user_agent_and_fields():
    client, recorder = make_client()

    data = client.lookup("8.8.8.8")

    request = recorder.requests[0]
    assert request.method == "GET"
    assert request.url.scheme == "https"
    assert request.url.host == "api.ipdata.co"
    assert request.url.path == "/8.8.8.8"
    assert request.url.params["api-key"] == "test"
    assert request.url.params["fields"] == ""
    assert request.headers["user-agent"] == f"ipdata-python/{ipdata_module.__version__}"
    assert re.fullmatch(r"ipdata-python/\S+", request.headers["user-agent"])
    assert request.headers["accept"] == "application/json"
    assert data.ip == "8.8.8.8"
    assert data.asn.name == "Google LLC"
    assert data.status == 200
    assert "endpoint" not in data


def test_lookup_fields_and_eu_endpoint():
    client, recorder = make_client(
        endpoint="https://eu-api.ipdata.co/", api_key="eu-key"
    )

    data = client.lookup("8.8.8.8", fields=["ip", "asn"])

    request = recorder.requests[0]
    assert request.url.host == "eu-api.ipdata.co"
    assert request.url.params["api-key"] == "eu-key"
    assert request.url.params["fields"] == "ip,asn"
    assert data.endpoint == "EU"


def test_lookup_select_field_ipv6_and_asn_paths():
    client, recorder = make_client()

    client.lookup("2620:11a:a000::", select_field="asn")
    client.lookup("as15169")
    client.lookup()

    # lookup() upper-cases the resource so that typoed ASNs such as "as15169" still work
    assert [r.url.path for r in recorder.requests] == ["/2620:11A:A000::", "/AS15169", "/"]
    assert recorder.requests[0].url.params["fields"] == "asn"


def test_lookup_validation_happens_before_any_request():
    client, recorder = make_client()

    with pytest.raises(ValueError):
        client.lookup("10.0.0.1")  # reserved address
    with pytest.raises(ValueError):
        client.lookup("8.8.8.8", fields=["nope"])
    with pytest.raises(ValueError):
        client.lookup("8.8.8.8", fields="ip")
    with pytest.raises(ValueError):
        client.lookup("8.8.8.8", fields=["ip"], select_field="asn")
    assert recorder.requests == []


def test_lookup_invalid_json_raises_ipdata_exception():
    client, _ = make_client(httpx.Response(200, text="<html>not json</html>"))

    with pytest.raises(IPDataException, match="decoding the API response"):
        client.lookup("8.8.8.8")


def test_lookup_returns_error_payload_with_status():
    client, _ = make_client(httpx.Response(401, json={"message": "You have not provided a valid API Key."}))

    data = client.lookup("8.8.8.8")

    assert data.status == 401
    assert data.message.startswith("You have not provided")


def test_dotdict_wraps_dict_list_items_and_leaves_the_others_alone():
    data = DotDict(
        {
            "numbers": [1, 2, 3],
            "mixed": [{"name": "a"}, "b", None],
            "nested": {"entries": [{"name": "c"}]},
        }
    )

    # dot access to a list of scalars used to raise TypeError
    assert data.numbers == [1, 2, 3]
    assert data.mixed[0].name == "a"
    assert data.mixed[1:] == ["b", None]
    assert data.nested.entries[0].name == "c"
    assert data.missing is None


def test_bulk_posts_json_with_the_client_timeout():
    responses = [dict(LOOKUP_RESPONSE), dict(LOOKUP_RESPONSE, ip="1.1.1.1")]
    client, recorder = make_client(httpx.Response(200, json=responses), timeout=7)

    data = client.bulk(["8.8.8.8", "1.1.1.1"], fields=["ip", "asn"])

    request = recorder.requests[0]
    assert request.method == "POST"
    assert request.url.path == "/bulk"
    assert request.url.params["api-key"] == "test"
    assert request.url.params["fields"] == "ip,asn"
    assert request.headers["content-type"] == "application/json"
    assert json.loads(request.content) == ["8.8.8.8", "1.1.1.1"]
    # bulk() previously sent its request without any timeout; it now uses the client timeout
    assert request.extensions["timeout"] == {"connect": 7, "read": 7, "write": 7, "pool": 7}
    assert [r.ip for r in data.responses] == ["8.8.8.8", "1.1.1.1"]
    assert data.status == 200


def test_lookup_uses_the_default_timeout():
    client, recorder = make_client()

    client.lookup("8.8.8.8")

    assert recorder.requests[0].extensions["timeout"] == {"connect": 60, "read": 60, "write": 60, "pool": 60}


def test_bulk_accepts_a_set_of_resources():
    responses = [dict(LOOKUP_RESPONSE), dict(LOOKUP_RESPONSE, ip="1.1.1.1")]
    client, recorder = make_client(httpx.Response(200, json=responses))

    data = client.bulk({"8.8.8.8", "1.1.1.1"}, fields=["ip"])

    # a set passes the validation but is not JSON serialisable, so it is sent as a list
    assert sorted(json.loads(recorder.requests[0].content)) == ["1.1.1.1", "8.8.8.8"]
    assert data.status == 200
    assert [r.ip for r in data.responses] == ["8.8.8.8", "1.1.1.1"]


def test_bulk_non_200_returns_payload_with_status():
    client, _ = make_client(httpx.Response(403, json={"message": "Forbidden"}))

    data = client.bulk(["8.8.8.8"])

    assert data == {"message": "Forbidden", "status": 403}


def test_bulk_validation_happens_before_any_request():
    client, recorder = make_client()

    with pytest.raises(ValueError):
        client.bulk("8.8.8.8")
    with pytest.raises(ValueError):
        client.bulk([])
    with pytest.raises(ValueError):
        client.bulk(["8.8.8.8"], fields=["nope"])
    assert recorder.requests == []


def test_retry_schedule_on_server_errors(sleeps):
    client, recorder = make_client(
        httpx.Response(503, json={"message": "Service Unavailable"}),
        httpx.Response(502, text="Bad Gateway"),
        httpx.Response(500, json={"message": "Internal server error"}),
        httpx.Response(504, text="Gateway Timeout"),
        httpx.Response(200, json=LOOKUP_RESPONSE),
    )

    data = client.lookup("8.8.8.8")

    assert len(recorder.requests) == 5
    assert sleeps == [0.5, 1, 2, 4]
    assert data.status == 200
    assert data.ip == "8.8.8.8"


def test_retry_schedule_uses_the_backoff_factor(sleeps):
    client, recorder = make_client(
        *[httpx.Response(503, text="Service Unavailable")] * 7,
        httpx.Response(200, json=LOOKUP_RESPONSE),
        retry_backoff_factor=2,
    )

    data = client.lookup("8.8.8.8")

    assert len(recorder.requests) == 8
    assert sleeps == [1, 2, 4, 8, 16, 32, 64]
    assert data.status == 200


def test_full_default_schedule_then_last_response_is_returned(sleeps):
    client, recorder = make_client(httpx.Response(503, json={"message": "Service Unavailable"}))

    data = client.lookup("8.8.8.8")

    # 1 request + 7 retries, with the documented sleeps in between
    assert len(recorder.requests) == 8
    assert sleeps == [0.5, 1, 2, 4, 8, 16, 32]
    assert data.status == 503


def test_retry_limit_is_honoured_for_bulk(sleeps):
    client, recorder = make_client(httpx.Response(500, json={"message": "Internal server error"}), retry_limit=3)

    data = client.bulk(["8.8.8.8"])

    assert len(recorder.requests) == 4
    assert all(r.method == "POST" for r in recorder.requests)
    assert sleeps == [0.5, 1, 2]
    assert data == {"message": "Internal server error", "status": 500}


def test_retry_on_transport_errors(sleeps):
    client, recorder = make_client(
        httpx.ConnectError("connection refused"),
        httpx.ReadTimeout("timed out"),
        httpx.RemoteProtocolError("Server disconnected without sending a response."),
        httpx.Response(200, json=LOOKUP_RESPONSE),
    )

    data = client.lookup("8.8.8.8")

    assert len(recorder.requests) == 4
    assert sleeps == [0.5, 1, 2]
    assert data.status == 200


def test_bulk_retries_a_request_that_died_on_a_stale_connection(sleeps):
    client, recorder = make_client(
        httpx.RemoteProtocolError("Server disconnected without sending a response."),
        httpx.Response(200, json=[LOOKUP_RESPONSE]),
    )

    data = client.bulk(["8.8.8.8"])

    assert len(recorder.requests) == 2
    assert sleeps == [0.5]
    assert data.responses[0].ip == "8.8.8.8"


def test_exhausted_transport_errors_raise_ipdata_exception(sleeps):
    client, recorder = make_client(httpx.ConnectError("connection refused"), retry_limit=2)

    with pytest.raises(IPDataException, match="connection refused"):
        client.lookup("8.8.8.8")
    assert len(recorder.requests) == 3
    assert sleeps == [0.5, 1]

    with pytest.raises(IPDataException, match="Error when looking up"):
        client.bulk(["8.8.8.8"])
    assert len(recorder.requests) == 6


def test_retry_limit_zero_disables_retries(sleeps):
    client, recorder = make_client(httpx.Response(503, json={"message": "Service Unavailable"}), retry_limit=0)
    data = client.lookup("8.8.8.8")
    assert data.status == 503
    assert len(recorder.requests) == 1

    client, recorder = make_client(httpx.ConnectError("connection refused"), retry_limit=0)
    with pytest.raises(IPDataException):
        client.lookup("8.8.8.8")
    assert len(recorder.requests) == 1
    assert sleeps == []


def test_429_without_retry_after_fails_fast(sleeps):
    client, recorder = make_client(httpx.Response(429, json={"message": "You have exceeded your quota."}))

    data = client.lookup("8.8.8.8")

    assert len(recorder.requests) == 1
    assert sleeps == []
    assert data.status == 429
    assert data.message == "You have exceeded your quota."


def test_429_with_retry_after_seconds_is_retried(sleeps):
    client, recorder = make_client(
        httpx.Response(429, headers={"Retry-After": "2"}, json={"message": "slow down"}),
        httpx.Response(200, json=LOOKUP_RESPONSE),
    )

    data = client.lookup("8.8.8.8")

    assert len(recorder.requests) == 2
    assert sleeps == [2.0]
    assert data.status == 200


def test_429_retry_after_is_capped_at_60_seconds(sleeps):
    client, recorder = make_client(
        httpx.Response(429, headers={"Retry-After": "600"}, json={"message": "slow down"}),
        httpx.Response(200, json=LOOKUP_RESPONSE),
    )

    client.lookup("8.8.8.8")

    assert sleeps == [60.0]


def test_429_retry_after_http_date(sleeps):
    when = datetime.now(timezone.utc) + timedelta(seconds=30)
    client, recorder = make_client(
        httpx.Response(429, headers={"Retry-After": format_datetime(when, usegmt=True)}, json={}),
        httpx.Response(200, json=LOOKUP_RESPONSE),
    )

    client.lookup("8.8.8.8")

    assert len(sleeps) == 1
    assert 25 < sleeps[0] <= 30


def test_429_with_unparseable_retry_after_uses_the_backoff(sleeps):
    client, recorder = make_client(
        httpx.Response(429, headers={"Retry-After": "soon"}, json={}),
        httpx.Response(200, json=LOOKUP_RESPONSE),
    )

    client.lookup("8.8.8.8")

    assert sleeps == [0.5]


def test_429_retries_count_against_the_retry_limit(sleeps):
    client, recorder = make_client(
        httpx.Response(429, headers={"Retry-After": "1"}, json={"message": "slow down"}), retry_limit=2
    )

    data = client.lookup("8.8.8.8")

    assert len(recorder.requests) == 3
    assert sleeps == [1.0, 1.0]
    assert data.status == 429


def test_requests_share_one_transport_and_client():
    recorder = Recorder(httpx.Response(200, json=LOOKUP_RESPONSE), httpx.Response(200, json=LOOKUP_RESPONSE), httpx.Response(200, json=[LOOKUP_RESPONSE]))
    transport = httpx.MockTransport(recorder)
    client = IPData("test", transport=transport)
    http_client = client._client
    assert isinstance(http_client, httpx.Client)
    assert http_client._transport is transport

    client.lookup("8.8.8.8")
    client.lookup("1.1.1.1")
    client.bulk(["8.8.8.8"])

    # all three calls went through the same transport object and the same httpx.Client
    assert len(recorder.requests) == 3
    assert client._client is http_client
    assert http_client._transport is transport
    assert not http_client.is_closed


def test_close_and_context_manager():
    client, recorder = make_client()
    with client as entered:
        assert entered is client
        client.lookup("8.8.8.8")
        assert not client._client.is_closed
    assert client._client.is_closed
    # a closed client can not be used again, and the failure surfaces as the usual IPDataException
    with pytest.raises(IPDataException):
        client.lookup("8.8.8.8")
    assert len(recorder.requests) == 1

    client, _ = make_client()
    client.close()
    client.close()  # closing twice is harmless
    assert client._client.is_closed


def test_default_transport_pool_configuration():
    client = IPData("test")
    try:
        assert isinstance(client._client._transport, httpx.HTTPTransport)
        pool = client._client._transport._pool
        assert pool._keepalive_expiry == 60.0
        assert pool._max_connections == 20
        assert pool._max_keepalive_connections == 20
        assert pool._http2 is True
        assert client._client.headers["user-agent"] == f"ipdata-python/{ipdata_module.__version__}"
        assert client._client.params["api-key"] == "test"
        assert client._client.timeout == httpx.Timeout(60)
    finally:
        client.close()

    client = IPData("test", http2=False)
    try:
        assert client._client._transport._pool._http2 is False
    finally:
        client.close()


def test_module_level_helpers_reuse_one_default_client(monkeypatch):
    recorder = Recorder(httpx.Response(200, json=LOOKUP_RESPONSE), httpx.Response(200, json=LOOKUP_RESPONSE), httpx.Response(200, json=[LOOKUP_RESPONSE]))
    client = IPData("test", transport=httpx.MockTransport(recorder))
    monkeypatch.setattr(ipdata, "default_client", client)

    ipdata.lookup("8.8.8.8")
    ipdata.lookup("1.1.1.1", fields=["ip"])
    ipdata.bulk(["8.8.8.8"])

    assert ipdata.default_client is client
    assert len(recorder.requests) == 3
    assert recorder.requests[1].url.params["fields"] == "ip"
