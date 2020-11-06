# Getting Started

This is a Python client and command line interface (CLI) for the [ipdata.co](https://ipdata.co) IP Geolocation API. ipdata offers a fast, highly-available API to enrich IP Addresses with Location, Company, Threat Intelligence and numerous other data attributes.

Note you need an API Key to access the API. To get a key on the 1500 requests a day free tier, sign up at https://ipdata.co/registration.html. If you need higher volume, sign up for your preferred plan at https://ipdata.co/pricing.html.

Visit our [Documentation](https://docs.ipdata.co/) for more information.

## Installation

```
pip3 install ipdata
```

## Usage

### Looking Up the Calling IP Address

```
from ipdata import ipdata
from pprint import pprint
# Create an instance of an ipdata object. Replace `test` with your API Key
ipdata = ipdata.IPData('test')
response = ipdata.lookup()
pprint(response)
```

### Looking Up any IP Address

```
from ipdata import ipdata
from pprint import pprint
# Create an instance of an ipdata object. Replace `test` with your API Key
ipdata = ipdata.IPData('test')
response = ipdata.lookup('69.78.70.144')
pprint(response)
```

Response

```
{'asn': 'AS6167',
 'calling_code': '1',
 'carrier': {'mcc': '310', 'mnc': '004', 'name': 'Verizon'},
 'city': 'Farmersville',
 'continent_code': 'NA',
 'continent_name': 'North America',
 'count': '1506',
 'country_code': 'US',
 'country_name': 'United States',
 'currency': {'code': 'USD',
              'name': 'US Dollar',
              'native': '$',
              'plural': 'US dollars',
              'symbol': '$'},
 'emoji_flag': '🇺🇸',
 'emoji_unicode': 'U+1F1FA U+1F1F8',
 'flag': 'https://ipdata.co/flags/us.png',
 'ip': '69.78.70.144',
 'is_eu': False,
 'languages': [{'name': 'English', 'native': 'English'}],
 'latitude': 33.1659,
 'longitude': -96.3686,
 'organisation': 'Cellco Partnership DBA Verizon Wireless',
 'postal': '75442',
 'region': 'Texas',
 'region_code': 'TX',
 'status': 200,
 'threat': {'is_anonymous': False,
            'is_bogon': False,
            'is_known_abuser': False,
            'is_known_attacker': False,
            'is_proxy': False,
            'is_threat': False,
            'is_tor': False},
 'time_zone': {'abbr': 'CDT',
               'current_time': '2019-04-28T17:56:59.246755-05:00',
               'is_dst': True,
               'name': 'America/Chicago',
               'offset': '-0500'}}
```

### Getting only one field

```
from ipdata import ipdata
from pprint import pprint
# Create an instance of an ipdata object. Replace `test` with your API Key
ipdata = ipdata.IPData('test')
response = ipdata.lookup('8.8.8.8', select_field='organisation')
pprint(response)
```

Response

```
{'organisation': 'Google LLC', 'status': 200}
```

### Getting a number of specific fields

```
from ipdata import ipdata
from pprint import pprint
# Create an instance of an ipdata object. Replace `test` with your API Key
ipdata = ipdata.IPData('test')
response = ipdata.lookup('8.8.8.8',fields=['ip','organisation','country_name'])
pprint(response)
```

Response

```
{'country_name': 'United States',
 'ip': '8.8.8.8',
 'organisation': 'Google LLC',
 'status': 200}
```

### Bulk Lookups

```
from ipdata import ipdata
from pprint import pprint
# Create an instance of an ipdata object. Replace `test` with your API Key
ipdata = ipdata.IPData('test')
response = ipdata.bulk_lookup(['8.8.8.8','1.1.1.1'])
pprint(response)
```

Response

```
{'responses': [{'asn': 'AS15169',
               'calling_code': '1',
               'city': None,
               'continent_code': 'NA',
               'continent_name': 'North America',
               'count': '1506',
               'country_code': 'US',
               'country_name': 'United States',
               'currency': {'code': 'USD',
                            'name': 'US Dollar',
                            'native': '$',
                            'plural': 'US dollars',
                            'symbol': '$'},
               'emoji_flag': '🇺🇸',
               'emoji_unicode': 'U+1F1FA U+1F1F8',
               'flag': 'https://ipdata.co/flags/us.png',
               'ip': '8.8.8.8',
               'is_eu': False,
               'languages': [{'name': 'English', 'native': 'English'}],
               'latitude': 37.751,
               'longitude': -97.822,
               'organisation': 'Google LLC',
               'postal': None,
               'region': None,
               'region_code': None,
               'threat': {'is_anonymous': False,
                          'is_bogon': False,
                          'is_known_abuser': False,
                          'is_known_attacker': False,
                          'is_proxy': False,
                          'is_threat': False,
                          'is_tor': False},
               'time_zone': {'abbr': 'CDT',
                             'current_time': '2019-04-28T18:02:48.035425-05:00',
                             'is_dst': True,
                             'name': 'America/Chicago',
                             'offset': '-0500'}},
              {'asn': 'AS13335',
               'calling_code': '61',
               'city': None,
               'continent_code': 'OC',
               'continent_name': 'Oceania',
               'count': '1506',
               'country_code': 'AU',
               'country_name': 'Australia',
               'currency': {'code': 'AUD',
                            'name': 'Australian Dollar',
                            'native': '$',
                            'plural': 'Australian dollars',
                            'symbol': 'AU$'},
               'emoji_flag': '🇦🇺',
               'emoji_unicode': 'U+1F1E6 U+1F1FA',
               'flag': 'https://ipdata.co/flags/au.png',
               'ip': '1.1.1.1',
               'is_eu': False,
               'languages': [{'name': 'English', 'native': 'English'}],
               'latitude': -33.494,
               'longitude': 143.2104,
               'organisation': 'Cloudflare, Inc.',
               'postal': None,
               'region': None,
               'region_code': None,
               'threat': {'is_anonymous': False,
                          'is_bogon': False,
                          'is_known_abuser': False,
                          'is_known_attacker': False,
                          'is_proxy': False,
                          'is_threat': False,
                          'is_tor': False},
               'time_zone': {'abbr': 'AEST',
                             'current_time': '2019-04-29T09:02:48.036287+10:00',
                             'is_dst': False,
                             'name': 'Australia/Sydney',
                             'offset': '+1000'}}],
 'status': 200}
```

## Available Fields

A list of all the fields returned by the API is maintained at [Response Fields](https://docs.ipdata.co/api-reference/response-fields)

## Errors

A list of possible errors is available at [Status Codes](https://docs.ipdata.co/api-reference/status-codes)

## Tests

To run all tests

```
python3 test_ipdata.py
```

## ipdata CLI

Usage: `ipdata [OPTIONS] COMMAND [ARGS]...`

Options:
  `--api-key` TEXT IPData API Key

Commands:
  `batch`
  `info`
  `init`
  `me`

### ipdata CLI Examples

#### Initialize with API Key
```
ipdata init <API Key>
```
You may also pass `--api-key <API Key>` extra param to any command to
specify API Key.

#### Lookup your own IP address
```
ipdata
```
or
```
ipdata me
```
#### Look up an IP address
```
ipdata <IP Address>
```
#### Look up an I address and filter result by specifying coma separated list of fields 
```
ipdata <IP Address> --fields ip,country_code
```
#### Batch lookup
```
ipdata <file with IP addresses> --output <file to output>
```
#### Batch lookup with output to CSV file
```
ipdata <file with IP addresses> --output <file to output> --output-format CSV --fields ip,country_code
```
`--fields` option is required in case of CSV output.
