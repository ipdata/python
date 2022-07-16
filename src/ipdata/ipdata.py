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

import os
import ipaddress
import requests
import logging
import urllib3
import functools

from requests.adapters import HTTPAdapter, Retry
from rich.logging import RichHandler

FORMAT = "%(message)s"
logging.basicConfig(
    level="ERROR", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)


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

    :param api_key: A valid IPData API key
    :param endpoint: The API endpoint to send requests to
    :param timeout: The default requests timeout
    :param retry_limit: The maximum number of retries in case of failure
    :param retry_backoff_factor: The number of seconds to sleep in between retries. With a 1 second backoff calls with be retried up to 7 times at the following intervals: 0.5, 1, 2, 4, 8, 16, 32
    :param debug: A boolean used to set the log level. Set to True when debugging.
    """

    log = logging.getLogger("rich")

    valid_fields = {
        "ip",
        "is_eu",
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
        api_key=os.environ.get("IPDATA_API_KEY"),
        endpoint="https://api.ipdata.co/",
        timeout=60,
        retry_limit=7,
        retry_backoff_factor=1,
        debug=False,
    ):
        if not api_key:
            raise IPDataException("API Key not set. Set an API key via the 'IPDATA_API_KEY' environment variable or see the docs for other ways to do so.")
        # Request settings
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")  # remove trailing /
        self._timeout = timeout
        self._headers = {"user-agent": "ipdata-python"}  # set default UserAgent
        self._query_params = {"api-key": self.api_key}

        # Enable debugging
        if debug:
            self.log.setLevel(logging.DEBUG)

        # Work around renamed argument in urllib3.
        if hasattr(urllib3.util.Retry.DEFAULT, "allowed_methods"):
            methods_arg = "allowed_methods"
        else:
            methods_arg = "method_whitelist"

        # Retry settings
        retry_args = {
            "total": retry_limit,
            "backoff_factor": retry_backoff_factor,
            "status_forcelist": [429, 500, 502, 503, 504],
            methods_arg: {"POST"},
        }

        adapter = HTTPAdapter(max_retries=urllib3.Retry(**retry_args))

        self._session = requests.Session()
        self._session.mount("http", adapter)

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

    def lookup(self, resource="", fields=[]):
        """
        Makes a GET request to the IPData API for the specified 'resource' and the given 'fields'.

        :param resource: Either an IP address or an ASN prefixed by "AS" eg. "AS15169"
        :param fields: A collection of API fields to be returned

        :returns: An API response as a DotDict object to allow dot notation access of fields eg. data.ip, data.company.name, data.threat.blocklists[0].name etc

        :raises IPDataException: if the API call fails or if there is a failure in decoding the response.
        :raises ValueError: if 'resource' is not a string
        """
        if type(resource) is not str:
            raise ValueError(f"{resource} must be of type 'str'")

        resource = (
            resource.upper()
        )  # capitalize resource in case it's a typoed ASN query eg. as2

        if resource and not resource.startswith("AS"):
            self._validate_ip_address(resource)

        self._validate_fields(fields)
        query_params = self._query_params | {"fields": ",".join(fields)}

        # Make the request
        try:
            response = self._session.get(
                f"{self.endpoint}/{resource}",
                headers=self._headers,
                params=query_params,
                timeout=self._timeout,
            )
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
        query_params = self._query_params | {"fields": ",".join(fields)}

        # Make the requests
        try:
            response = self._session.post(
                f"{self.endpoint}/bulk",
                headers=self._headers,
                params=query_params,
                json=resources,
            )
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
