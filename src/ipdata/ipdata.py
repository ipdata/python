"""This is the official IPData client library for Python.

IPData client libraries allow for looking up the geolocation,
ownership and threat profile or any IP address and ASN.

Example:
    >>> from ipdata import IPData
    >>> ipdata = IPData("YOUR API KEY")
    >>> ipdata.lookup() # or ipdata.lookup("8.8.8.8")

Alternatively thanks to the convenience methods in __init__.py you can do

Example
    >>> import ipdata
    >>> ipdata.api_key = <YOUR API KEY>
    >>> ipdata.lookup() # or ipdata.lookup("8.8.8.8") 

:class:`~.IPData` is the primary class for making API requests.
"""

import email.utils
import importlib.metadata
import ipaddress
import logging
import os
import time
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

try:
    __version__ = importlib.metadata.version("ipdata")
except importlib.metadata.PackageNotFoundError:  # running from a source checkout
    __version__ = "unknown"

# HTTP statuses that are retried, for GET and POST requests alike
RETRY_STATUSES = frozenset({500, 502, 503, 504})
# Longest pause honoured from a 429 Retry-After header, in seconds
MAX_RETRY_AFTER = 60.0

# Seam for the tests, which replace it to check the retry schedule without sleeping
_sleep = time.sleep


class IPDataException(Exception):
    pass


class DotDict(dict):
    """
    dot.notation access to dictionary attributes
    Based on https://stackoverflow.com/a/23689767/3176550
    """

    def __getattr__(*args):
        val = dict.get(*args)
        if type(val) is dict:
            return DotDict(val)
        elif type(val) is list:
            return [DotDict(item) for item in val]
        return val

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class IPData(object):
    """
    Instances of IPData are used to make API requests. To make requests to the EU endpoint, set "endpoint" to "https://eu-api.ipdata.co".

    Every instance owns one HTTPS connection pool that is kept alive and reused for all of its requests
    (multiplexed over HTTP/2 when the server negotiates it, HTTP/1.1 keep-alive otherwise), so create one
    client per process (or per API key or endpoint), reuse it for every lookup and call :meth:`close` (or use
    the instance as a context manager) when you are done with it. Instances are thread-safe. A client must
    be created after forking: never share one across os.fork() or multiprocessing boundaries.

    Failed requests are retried up to 'retry_limit' times. GET and POST requests that fail with a transport
    error (connection reset, timeout, ...) or with HTTP 500, 502, 503 or 504 are retried after sleeping
    retry_backoff_factor * 2 ** (attempt - 2) seconds, i.e. 0.5, 1, 2, 4, 8, 16 and 32 seconds with the
    defaults. HTTP 429 is retried only when the response carries a Retry-After header (sleeping at most 60
    seconds); without one the response is returned immediately so that an exhausted quota fails fast.

    :param api_key: A valid IPData API key
    :param endpoint: The API endpoint to send requests to
    :param timeout: The default requests timeout in seconds, applied to every request including bulk lookups
    :param retry_limit: The maximum number of retries in case of failure
    :param retry_backoff_factor: The number of seconds to sleep in between retries. With a 1 second backoff calls with be retried up to 7 times at the following intervals: 0.5, 1, 2, 4, 8, 16, 32
    :param debug: A boolean used to set the log level. Set to True when debugging.
    :param http2: Negotiate HTTP/2 with automatic fallback to HTTP/1.1. Set to False to use HTTP/1.1 keep-alive only.
    :param transport: An optional httpx.BaseTransport used instead of the default HTTPS transport, for example an httpx.MockTransport in tests
    """

    log = logging.getLogger(__name__)

    valid_fields = {
        "ip",
        "is_eu",
        "is_satellite",
        "is_anycast",
        "city",
        "region",
        "region_code",
        "country_name",
        "country_code",
        "continent_name",
        "continent_code",
        "latitude",
        "longitude",
        "asn",
        "postal",
        "calling_code",
        "flag",
        "emoji_flag",
        "emoji_unicode",
        "carrier",
        "languages",
        "currency",
        "time_zone",
        "threat",
        "count",
        "status",
        "company",
    }

    def __init__(
        self,
        api_key=None,
        endpoint="https://api.ipdata.co/",
        timeout=60,
        retry_limit=7,
        retry_backoff_factor=1,
        debug=False,
        http2=True,
        transport=None,
    ):
        if api_key is None:
            api_key = os.environ.get("IPDATA_API_KEY")
        if not api_key:
            raise IPDataException("API Key not set. Set an API key via the 'IPDATA_API_KEY' environment variable or see the docs for other ways to do so.")
        # Request settings
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")  # remove trailing /
        self._timeout = timeout
        self._retry_limit = retry_limit
        self._retry_backoff_factor = retry_backoff_factor
        self._headers = {
            "user-agent": f"ipdata-python/{__version__}",  # set default UserAgent
            "accept": "application/json",
        }
        self._query_params = {"api-key": self.api_key}

        # Enable debugging
        if debug:
            self.log.setLevel(logging.DEBUG)
            if not any(
                not isinstance(h, logging.NullHandler) for h in self.log.handlers
            ):
                from rich.logging import RichHandler
                handler = RichHandler()
                handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
                self.log.addHandler(handler)

        # One connection pool per client instance. Connections are kept alive for 60 seconds and reused
        # across requests (multiplexed over HTTP/2 when the server negotiates it, HTTP/1.1 keep-alive
        # otherwise) instead of paying a TCP + TLS handshake per call. When no transport is injected
        # httpx builds its default one, which honours HTTPS_PROXY / NO_PROXY and the SSL_CERT_* variables
        # like requests did; with an injected transport httpx uses it as-is and ignores http2 and limits.
        self._client = httpx.Client(
            base_url=self.endpoint,
            http2=http2,
            timeout=httpx.Timeout(timeout),
            headers=self._headers,
            params=self._query_params,
            limits=httpx.Limits(
                max_connections=20, max_keepalive_connections=20, keepalive_expiry=60.0
            ),
            transport=transport,
        )

    def close(self):
        """
        Closes the connection pool. The instance can not be used afterwards. Call this at shutdown, or use the instance as a context manager:

            >>> with IPData("YOUR API KEY") as ipdata:
            ...     ipdata.lookup("8.8.8.8")
        """
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _validate_fields(self, fields):
        """
        Validates the fields passed in by the user, first ensuring it's a collection. In prior versions 'fields' was a string, however it now needs to be a collection.

        :param fields: A collection of supported fields
        :raises ValueError: if 'fields' is not one of ['list', 'tuple' or 'set'] or if 'fields' contains unsupported fields
        """
        if not type(fields) in [list, set, tuple]:
            raise ValueError("'fields' must be of type 'list', 'tuple' or 'set'.")

        # Get all unsupported fields
        diff = set(fields).difference(self.valid_fields)
        if diff:
            raise ValueError(
                f"The field(s) {diff} are not supported. Only {self.valid_fields} are supported."
            )

    def _validate_ip_address(self, ip):
        """
        Checks that 'ip' is a valid IP Address.

        :param ip: A string
        :raises ValueError: if 'ip' is either not a valid IP address or is a reserved IP address eg. private, reserved or multicast
        """
        request_ip = ipaddress.ip_address(ip)
        if request_ip.is_private or request_ip.is_reserved or request_ip.is_multicast:
            raise ValueError(f"{ip} is a reserved IP Address")

    def _backoff(self, attempt):
        """
        Seconds to sleep before retry number 'attempt' (1-based): 0.5, 1, 2, 4, 8, 16, 32 with the default backoff factor.
        """
        return self._retry_backoff_factor * 2 ** (attempt - 2)

    @staticmethod
    def _retry_after(value):
        """
        Parses a Retry-After header, given either as delay-seconds or as an HTTP-date.

        :returns: The number of seconds to wait, or None if the value can not be parsed
        """
        value = value.strip()
        if value.isdigit():
            return float(value)
        try:
            when = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return max((when - datetime.now(timezone.utc)).total_seconds(), 0.0)

    def _request(self, method, path, **kwargs):
        """
        Sends a request over the shared connection pool, retrying it as described in the class docstring.

        :returns: The last httpx.Response received
        :raises httpx.TransportError: if the request still fails to get a response once the retries are exhausted
        """
        attempt = 0
        while True:
            attempt += 1
            try:
                response = self._client.request(method, path, **kwargs)
            except httpx.UnsupportedProtocol:
                raise  # a configuration error that no retry can fix
            except httpx.TransportError as e:
                if attempt > self._retry_limit:
                    raise
                delay = self._backoff(attempt)
                reason = f"{type(e).__name__}: {e}"
            else:
                status_code = response.status_code
                if attempt > self._retry_limit:
                    return response
                if status_code in RETRY_STATUSES:
                    delay = self._backoff(attempt)
                elif status_code == 429 and "retry-after" in response.headers:
                    delay = self._retry_after(response.headers["retry-after"])
                    if delay is None:
                        delay = self._backoff(attempt)
                    delay = min(delay, MAX_RETRY_AFTER)
                else:
                    return response
                reason = f"HTTP {status_code}"
            self.log.debug(
                "Retrying %s %s in %.1fs (retry %d of %d) after %s",
                method,
                path,
                delay,
                attempt,
                self._retry_limit,
                reason,
            )
            _sleep(delay)

    def lookup(self, resource="", fields=[], select_field=None):
        """
        Makes a GET request to the IPData API for the specified 'resource' and the given 'fields'.

        :param resource: Either an IP address or an ASN prefixed by "AS" eg. "AS15169"
        :param fields: A collection of API fields to be returned
        :param select_field: A single field name to return (convenience alternative to fields)

        :returns: An API response as a DotDict object to allow dot notation access of fields eg. data.ip, data.company.name, data.threat.blocklists[0].name etc

        :raises IPDataException: if the API call fails or if there is a failure in decoding the response.
        :raises ValueError: if 'resource' is not a string, or if both 'select_field' and 'fields' are provided
        """
        if type(resource) is not str:
            raise ValueError(f"{resource} must be of type 'str'")

        resource = (
            resource.upper()
        )  # capitalize resource in case it's a typoed ASN query eg. as2

        if resource and not resource.startswith("AS"):
            self._validate_ip_address(resource)

        if select_field is not None:
            if fields:
                raise ValueError("'select_field' and 'fields' are mutually exclusive. Use one or the other.")
            if not isinstance(select_field, str):
                raise ValueError("'select_field' must be of type 'str'.")
            fields = [select_field]

        self._validate_fields(fields)
        query_params = {"fields": ",".join(fields)}

        # Make the request
        try:
            response = self._request("GET", f"/{resource}", params=query_params)
        except Exception as e:
            raise IPDataException(e)

        status_code = response.status_code

        # Decode the response and add metadata
        try:
            data = DotDict(response.json())
            data["status"] = status_code
            if "eu-api" in self.endpoint:
                data["endpoint"] = "EU"
        except ValueError:
            raise IPDataException(
                f"An error occured while decoding the API response: {response.text}"
            )

        return data

    def bulk(self, resources, fields=[]):
        """
        Lookup up to 100 resources in one request. Makes a POST request wth the resources as a JSON array and the specified fields.

        :param resources: A list of resources. This can be a list of IP addresses or ASNs or a mix of both which is not recommended unless you handle it during parsing. Mixing resources might lead to weird behavior when writing results to CSV.
        :param fields: A collection of API fields to be returned.

        :returns: A DotDict object with the data contained under the 'responses' key.

        :raises ValueError: if resources it not a collection
        :raises ValueError: if resources contains 0 items
        :raises IPDataException: if the API call fails or if there is an error decoding the response
        """

        if type(resources) not in [list, set]:
            raise ValueError(f"{resources} must be of type 'list' or 'set'")

        if len(resources) < 1:
            raise ValueError("Bulk lookups must contain at least 1 resource.")

        self._validate_fields(fields)
        query_params = {"fields": ",".join(fields)}

        # Make the requests
        try:
            response = self._request("POST", "/bulk", params=query_params, json=resources)
        except Exception as e:
            raise IPDataException(f"Error when looking up {resources} - {e}")

        status_code = response.status_code

        # Decode the response
        try:
            data = response.json()
        except ValueError:
            raise IPDataException(
                f"An error occured while decoding the API response: {response.text}"
            )

        # If the request returned a non 200 response we add metadata and return the response
        if not status_code == 200:
            data["status"] = status_code
            return data

        result = DotDict(
            {
                "responses": [DotDict(resource) for resource in data],
                "status": status_code,
            }
        )
        if "eu-api" in self.endpoint:
            result["endpoint"] = "EU"
        return result
