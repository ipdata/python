"""
    Geofeeds classes used in the CLI for the validator.
"""
import csv
import hashlib
import ipaddress
import logging
import random
from pathlib import Path

import requests
from rich.logging import RichHandler

from .codes import COUNTRIES, REGION_CODES

FORMAT = "%(message)s"
logging.basicConfig(
    level="ERROR", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("rich")

pwd = Path(__file__).parent.resolve()


class GeofeedValidationError(Exception):
    pass


class Geofeed(object):
    """
    Create an instance of a Geofeed object.

    :param source: Either a URL or a local file containing geofeed formatted data according to https://datatracker.ietf.org/doc/html/draft-google-self-published-geofeeds-05.
    :param dir: The directory where the downloaded copy of a geofeed is cached
    """

    def __init__(self, source, dir="/tmp") -> None:
        self.source = source
        self.dir = dir
        self.cache_path = None
        self.total_count = 0
        self.valid_count = 0
        # Ensure uniqueness https://datatracker.ietf.org/doc/html/draft-google-self-published-geofeeds-05#appendix-A
        self.prefixes = set()

    def _download(self):
        """
        Downloads and caches the geofeed if a valid URL is provided

        :raises Exception: if a failure occurs when downloading the geofeed
        """
        random_name = hashlib.sha224( str(random.getrandbits(256)).encode('utf-8') ).hexdigest()[:16]
        cache_path = f"{self.dir}/{random_name}.csv"

        try:
            response = requests.get(self.source, timeout=60)
            text = response.text
            with open(cache_path, "w") as f:
                f.write(
                    "\n".join(
                        line for line in text.split("\n") if not line.startswith("#")
                    )
                )  # don't write comments
        except Exception:
            log.exception(f"Failed to get {self.source}")
        else:
            # set cache path if download was successful
            self.cache_path = cache_path

    def entries(self):
        """
        Reads each line in a geofeed and yields Entry objects, one for each line.

        :raises GeofeedValidationError: if it find a duplicate or if the expected CSV format is invalid eg. if the line has != 5 columns. There are a number of optional fields however the minimum number of commans should be present i.e. 4.
        Also note that though the RFC recommends simply discarding extra columns to allow for additional fields in the future, we strictly check for 5 columns to prevent breaking out CSV parsing.
        :yields: An Entry object
        """
        # set path to the source by default
        path = self.source

        # if the source is a url and we haven't already download it, try to download it and update path to the location of the download cache
        if "://" in self.source and not self.cache_path:
            self._download()
            path = self.cache_path
            # if path still contains a url it means the download was not successful in which case we yield nothing!
            if not path:
                log.warning(f"No cache path for {self.source} found. Download likely failed.")
                return

        with open(path) as f:
            reader = csv.reader(f)
            for entry in reader:
                # keep count of the number of entries
                self.total_count += 1

                # generate error if there are not exactly 5 fields
                if len(entry) != 5:
                    yield GeofeedValidationError(
                        f"[{entry}] is not a valid geofeed entry. The 'IP Range' and 'Country' fields are required however you must have the requisite minimum number of commas (currently 4) present"
                    )
                    return

                # instantiate an Entry object
                geofeed_entry = Entry(*entry)

                # check for duplicates and generate error if found
                if geofeed_entry.ip_range in self.prefixes:
                    yield GeofeedValidationError(
                        f"Duplicate prefixes found {geofeed_entry.ip_range}"
                    )
                    return

                self.prefixes.add(geofeed_entry.ip_range)

                # generate entry
                yield geofeed_entry

    def __iter__(self):
        yield from self.entries()

class Entry(object):
    """
    Create an instance of an Entry object

    :param ip_range: A valid IP address prefix
    :param country: A valid ISO 3166-1 alpha 2 country code
    :param region: A valid ISO 3166-1 alpha 2 subdivision code
    :param city: The city where the IP range is allocated
    :param postal_code: The postal code of the location the IP range is allocated
    """

    def __init__(
        self, ip_range, country, region=None, city=None, postal_code=None
    ) -> None:
        self.ip_range = ip_range
        self.country = country.upper()
        self.region = region
        self.city = city
        self.postal_code = postal_code
        self.row = [
            self.ip_range,
            self.country,
            self.region,
            self.city,
            self.postal_code,
        ]

    def __str__(self) -> str:
        return f"{self.ip_range},{self.country},{self.region},{self.city},{self.postal_code}"

    def validate(self):
        """
        Validation rules for geofeed entries. Note that though the spec states that all fields other than the IP range are optional, we require at the minimum at country code. Entries without a country code will not pass validation.

        :raises GeofeedValidationError: if any of the validation rules are violated
        """

        # 1. Each IP range field MUST be either a single IP address or an IP prefix in CIDR notation in conformance with section 3.1 of[RFC4632] for IPv4 or section 2.3 of [RFC4291] for IPv6.
        # Reference: https://datatracker.ietf.org/doc/html/draft-google-self-published-geofeeds-02#section-2.1.1.1

        try:
            ipaddress.ip_network(self.ip_range)
        except ValueError:
            raise GeofeedValidationError(
                f"[{self}] does not have a valid IP address or prefix"
            )

        # 2 (a) Country code must be present at a minimum

        if not self.country:
            raise GeofeedValidationError(f"[{self}] is missing a country code")

        # 2 (b) Country code must be a valid 2-letter ISO 3166-1 alpha 2 country code
        # Reference: https://datatracker.ietf.org/doc/html/draft-google-self-published-geofeeds-02#section-2.1.1.2
        if not self.country in COUNTRIES:
            raise GeofeedValidationError(
                f"[{self}] ({self.country}) is not a valid ISO 3166-1 alpha 2 subdivision code"
            )

        # The region code is optional, but if it exists we need to validate it
        if self.region:
            # 3 (a) The region field, if non-empty, MUST be a ISO region code conforming to ISO 3166-2 [ISO.3166.2].  Parsers SHOULD treat this field case-insensitively.
            # Reference: https://datatracker.ietf.org/doc/html/draft-google-self-published-geofeeds-02#section-2.1.1.3
            if not self.region in REGION_CODES:
                raise GeofeedValidationError(
                    f"[{self}] ({self.region}) is not a valid ISO 3166-1 alpha 2 region code"
                )

            # 3 (b) The region must be in the same country
            if not self.region.split("-")[0] == self.country:
                raise GeofeedValidationError(
                    f"[{self}] the region code provided is in a different country"
                )
