[![PyPI version](https://badge.fury.io/py/ipdata.svg)](https://badge.fury.io/py/ipdata) ![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/ipdata/python/python-publish.yml?branch=master)

# Official Python client library and CLI for the ipdata API

This is a Python client and command line interface (CLI) for the [ipdata.co](https://ipdata.co) IP Geolocation API. ipdata offers a fast, highly-available API to enrich IP Addresses with Location, Company, Threat Intelligence and numerous other data attributes.

Note that you need an API Key to use this package. You can get a free one with a 1,500 daily request limit by [Signing up here](https://ipdata.co/sign-up.html).

Visit our [Documentation](https://docs.ipdata.co/) for more examples and tutorials.

[![asciicast](https://asciinema.org/a/371292.svg)](https://asciinema.org/a/371292)

## Installation

Install the latest version of the cli with `pip`.

```bash
pip install ipdata
```

or `easy_install`

```bash
easy_install ipdata
```

## Library Usage

You need a valid API key from ipdata to use the library. You can get a free key by [Signing up here](https://ipdata.co/sign-up.html).

Replace `test` with your API Key in the following examples.

### Looking up the calling IP Address

You can look up the calling IP address, that is, the IP address of the computer you are running this on by not passing an IP address to the `lookup` method.

```python
>>> import ipdata
>>> ipdata.api_key = "<YOUR API KEY>"
>>> ipdata.lookup()
```

### Looking up any IP Address

You can look up any valid IPv4 or IPv6 address by passing it to the `lookup` method.

```python
>>> import ipdata
>>> ipdata.api_key = "<YOUR API KEY>"
>>> response = ipdata.lookup('69.78.70.144')
pprint(response)
```

<details><summary>Sample Response</summary>

```json
{
  "ip": "69.78.70.144",
  "is_eu": false,
  "city": null,
  "region": null,
  "region_code": null,
  "country_name": "United States",
  "country_code": "US",
  "continent_name": "North America",
  "continent_code": "NA",
  "latitude": 37.750999450683594,
  "longitude": -97.8219985961914,
  "postal": null,
  "calling_code": "1",
  "flag": "https://ipdata.co/flags/us.png",
  "emoji_flag": "\ud83c\uddfa\ud83c\uddf8",
  "emoji_unicode": "U+1F1FA U+1F1F8",
  "asn": {
    "asn": "AS6167",
    "name": "Verizon Business",
    "domain": "verizon.com",
    "route": "69.78.0.0/17",
    "type": "business"
  },
  "company": {
    "name": "Verizon Business",
    "domain": "verizon.com",
    "network": "69.78.0.0/17",
    "type": "business"
  },
  "carrier": {
    "name": "Verizon",
    "mcc": "310",
    "mnc": "004"
  },
  "languages": [
    {
      "name": "English",
      "native": "English",
      "code": "en"
    }
  ],
  "currency": {
    "name": "US Dollar",
    "code": "USD",
    "symbol": "$",
    "native": "$",
    "plural": "US dollars"
  },
  "time_zone": {
    "name": null,
    "abbr": null,
    "offset": null,
    "is_dst": null,
    "current_time": null
  },
  "threat": {
    "is_tor": false,
    "is_icloud_relay": false,
    "is_proxy": false,
    "is_datacenter": false,
    "is_anonymous": false,
    "is_known_attacker": false,
    "is_known_abuser": false,
    "is_threat": false,
    "is_bogon": false,
    "blocklists": []
  },
  "count": "3895",
  "status": 200
}
```
</details>


### Getting only one field

If you only need a single data attribute about an IP address you can extract it by passing a `select_field` parameter to the `lookup` method.

```python
>>> import ipdata
>>> ipdata.api_key = "<YOUR API KEY>"
>>> ipdata.lookup('8.8.8.8', select_field='asn')
```

Response

```json
{
  "asn": {
    "asn": "AS15169",
    "name": "Google LLC",
    "domain": "about.google",
    "route": "8.8.8.0/24",
    "type": "business"
  },
  "status": 200
}
```

### Getting a number of specific fields

If instead you need to get multiple specific fields you can pass a list of valid field names in a `fields` parameter.

```python
>>> import ipdata
>>> ipdata.api_key = "<YOUR API KEY>"
>>> ipdata.lookup('8.8.8.8',fields=['ip','asn','country_name'])
```

Response

```json
{
  "ip": "8.8.8.8",
  "asn": {
    "asn": "AS15169",
    "name": "Google LLC",
    "domain": "about.google",
    "route": "8.8.8.0/24",
    "type": "business"
  },
  "country_name": "United States",
  "status": 200
}
```

### Bulk Lookups

The API provides a `/bulk` endpoint that allows you to look up upto 100 IP addresses at a time. This is convenient for quickly clearing your backlog.

NOTE: Alternatively it is much simpler to process bulk lookups using the `ipdata` cli's `batch` command. All you need is a csv file with a list of IP addresses and you can get your results as either a JSON file or a CSV file! See the [CLI Bulk Lookup Documentation](https://docs.ipdata.co/command-line-interface/bulk-lookups-recommended) for details.

```python
>>> import ipdata
>>> ipdata.api_key = "<YOUR API KEY>"
>>> ipdata.bulk(['8.8.8.8','1.1.1.1'])
```

<details><summary>Sample Response</summary>

```
{
  "responses": [
    {
      "ip": "8.8.8.8",
      "is_eu": false,
      "city": null,
      "region": null,
      "region_code": null,
      "country_name": "United States",
      "country_code": "US",
      "continent_name": "North America",
      "continent_code": "NA",
      "latitude": 37.750999450683594,
      "longitude": -97.8219985961914,
      "postal": null,
      "calling_code": "1",
      "flag": "https://ipdata.co/flags/us.png",
      "emoji_flag": "\ud83c\uddfa\ud83c\uddf8",
      "emoji_unicode": "U+1F1FA U+1F1F8",
      "asn": {
        "asn": "AS15169",
        "name": "Google LLC",
        "domain": "about.google",
        "route": "8.8.8.0/24",
        "type": "business"
      },
      "company": {
        "name": "Google LLC",
        "domain": "google.com",
        "network": "8.8.8.0/24",
        "type": "business"
      },
      "languages": [
        {
          "name": "English",
          "native": "English",
          "code": "en"
        }
      ],
      "currency": {
        "name": "US Dollar",
        "code": "USD",
        "symbol": "$",
        "native": "$",
        "plural": "US dollars"
      },
      "time_zone": {
        "name": null,
        "abbr": null,
        "offset": null,
        "is_dst": null,
        "current_time": null
      },
      "threat": {
        "is_tor": false,
        "is_icloud_relay": false,
        "is_proxy": false,
        "is_datacenter": false,
        "is_anonymous": false,
        "is_known_attacker": false,
        "is_known_abuser": false,
        "is_threat": false,
        "is_bogon": false,
        "blocklists": []
      },
      "count": "3931"
    },
    {
      "ip": "1.1.1.1",
      "is_eu": null,
      "city": null,
      "region": null,
      "region_code": null,
      "country_name": null,
      "country_code": null,
      "continent_name": null,
      "continent_code": null,
      "latitude": null,
      "longitude": null,
      "postal": null,
      "calling_code": null,
      "flag": null,
      "emoji_flag": null,
      "emoji_unicode": null,
      "asn": {
        "asn": "AS13335",
        "name": "Cloudflare, Inc.",
        "domain": "cloudflare.com",
        "route": "1.1.1.0/24",
        "type": "business"
      },
      "company": {
        "name": "Cloudflare, Inc.",
        "domain": "cloudflare.com",
        "network": "1.1.1.0/24",
        "type": "business"
      },
      "languages": null,
      "currency": {
        "name": null,
        "code": null,
        "symbol": null,
        "native": null,
        "plural": null
      },
      "time_zone": {
        "name": null,
        "abbr": null,
        "offset": null,
        "is_dst": null,
        "current_time": null
      },
      "threat": {
        "is_tor": false,
        "is_icloud_relay": false,
        "is_proxy": false,
        "is_datacenter": false,
        "is_anonymous": false,
        "is_known_attacker": false,
        "is_known_abuser": false,
        "is_threat": false,
        "is_bogon": false,
        "blocklists": []
      },
      "count": "3931"
    }
  ],
  "status": 200
}
```
</details>

## Using the ipdata CLI


### Windows Installation Notes

IPData CLI needs [Python 3.9+](https://www.python.org/downloads/windows/). Python Windows installation program
provides PIP so you can install IPData CLI the same way:
```
pip install ipdata
```

### Available commands

```shell
ipdata --help
Usage: ipdata [OPTIONS] COMMAND [ARGS]...

  Welcome to the ipdata CLI

Options:
  --api-key TEXT  Your ipdata API Key. Get one for free from
                  https://ipdata.co/sign-up.html
  --help          Show this message and exit.

Commands:
  lookup*   Lookup resources by using the IPData class methods.
  batch     Batch command for doing fast bulk processing.
  init      Initialize the CLI by setting an API key.
  usage     Get today's usage.
  validate  Validates a geofeed file. 
```

### Initialize the cli with your API Key

You need a valid API key from ipdata to use the cli. You can get a free key by [Signing up here](https://ipdata.co/sign-up.html).

```shell
ipdata init <API Key>
 _           _       _
(_)_ __   __| | __ _| |_ __ _
| | '_ \ / _` |/ _` | __/ _` |
| | |_) | (_| | (_| | || (_| |
|_| .__/ \__,_|\__,_|\__\__,_|
  |_|

✨ Successfully initialized.     
```

You can also pass the `--api-key <API Key>` parameter to any command to specify a different API Key.

### Look up your own IP address

Running the `ipdata` command without any parameters will look up the IP address of the computer you are running the command on. Alternatively you can explicitly look up your own IP address by running `ipdata`.


```shell
ipdata
```

To pretty print the result pass the `-p` flag

```
╭────────────────────────────────╮ ╭────────────╮ ╭─────────────────╮ ╭──────────╮ ╭─────────────╮ ╭───────────────╮ ╭──────────────╮ ╭────────────────╮ ╭────────────────╮ ╭────────╮ ╭──────────────╮
│ ip                             │ │ is_eu      │ │ city            │ │ region   │ │ region_code │ │ country_name  │ │ country_code │ │ continent_name │ │ continent_code │ │ postal │ │ calling_code │
│ 24.24.24.24                    │ │ False      │ │ Syracuse        │ │ New York │ │ NY          │ │ United States │ │ US           │ │ North America  │ │ NA             │ │ 13261  │ │ 1            │
╰────────────────────────────────╯ ╰────────────╯ ╰─────────────────╯ ╰──────────╯ ╰─────────────╯ ╰───────────────╯ ╰──────────────╯ ╰────────────────╯ ╰────────────────╯ ╰────────╯ ╰──────────────╯
╭────────────────────────────────╮ ╭────────────╮ ╭─────────────────╮ ╭──────────╮                                                                                                                     
│ flag                           │ │ emoji_flag │ │ emoji_unicode   │ │ count    │                                                                                                                     
│ https://ipdata.co/flags/us.png │ │ 🇺🇸         │ │ U+1F1FA U+1F1F8 │ │ 4086     │                                                                                                                     
╰────────────────────────────────╯ ╰────────────╯ ╰─────────────────╯ ╰──────────╯                                                                                                                     
╭────────────────────────────────╮ ╭──────────────────╮ ╭─────────────────╮ ╭────────────────╮ ╭───────────────────────────────╮ ╭───────────────────────╮
│ asn                            │ │ company          │ │ languages       │ │ currency       │ │ time_zone                     │ │ threat                │
│ ├── asn                        │ │ ├── name         │ │ └──             │ │ ├── name       │ │ ├── name                      │ │ ├── is_tor            │
│ │   AS11351                    │ │ │   Rr-Route     │ │     ├── name    │ │ │   US Dollar  │ │ │   America/New_York          │ │ │   False             │
│ ├── name                       │ │ ├── domain       │ │     │   English │ │ ├── code       │ │ ├── abbr                      │ │ ├── is_icloud_relay   │
│ │   Charter Communications Inc │ │ │                │ │     ├── native  │ │ │   USD        │ │ │   EDT                       │ │ │   False             │
│ ├── domain                     │ │ ├── network      │ │     │   English │ │ ├── symbol     │ │ ├── offset                    │ │ ├── is_proxy          │
│ │   spectrum.com               │ │ │   24.24.0.0/19 │ │     └── code    │ │ │   $          │ │ │   -0400                     │ │ │   False             │
│ ├── route                      │ │ └── type         │ │         en      │ │ ├── native     │ │ ├── is_dst                    │ │ ├── is_datacenter     │
│ │   24.24.0.0/18               │ │     business     │ ╰─────────────────╯ │ │   $          │ │ │   True                      │ │ │   False             │
│ └── type                       │ ╰──────────────────╯                     │ └── plural     │ │ └── current_time              │ │ ├── is_anonymous      │
│     business                   │                                          │     US dollars │ │     2022-07-15T16:59:44-04:00 │ │ │   False             │
╰────────────────────────────────╯                                          ╰────────────────╯ ╰───────────────────────────────╯ │ ├── is_known_attacker │
                                                                                                                                 │ │   False             │
                                                                                                                                 │ ├── is_known_abuser   │
                                                                                                                                 │ │   False             │
                                                                                                                                 │ ├── is_threat         │
                                                                                                                                 │ │   False             │
                                                                                                                                 │ ├── is_bogon          │
                                                                                                                                 │ │   False             │
                                                                                                                                 │ └── blocklists        │
                                                                                                                                 │     []                │
                                                                                                                                 ╰───────────────────────╯                                                    
```

### Look up any IP address

You can pass any valid IPv4 or IPv6 address to the `ipdata` command to look it up. In case an invalid value is passed you will get the error `ERROR    'BLEH' does not appear to be an IPv4 or IPv6 address"`.

```shell
ipdata 8.8.8.8
```

### Copying results to clipboard

Use `-c` to copy the results to the clipboard!

```
ipdata 1.1.1.1 -f ip -f asn -c 
📋️ Copied result to clipboard!  
```

### Filtering results by a list of fields 

Use `--fields` to filter the responses 

```shell
ipdata --fields city --fields country_name'
```

or use `-f`

```shell
ipdata 1.1.1.1 -f ip -f asn
```

```json
{
  "ip": "1.1.1.1",
  "asn": {
    "asn": "AS13335",
    "name": "Cloudflare, Inc.",
    "domain": "cloudflare.com",
    "route": "1.1.1.0/24",
    "type": "business"
  },
  "status": 200
}
```

### Batch lookup

Perhaps the most useful command provided by the CLI is the ability to process a csv file with a list of IP addresses and write the results to file as either CSV or JSONL/NDJSON! It could be a list of tens of thousands to millions of IP addresses and it will all be processed and the results filtered to your liking!

When you use the JSON output format, the results are written to the output file you provide with one result per line. Each line being a valid and full JSON response object.
If you only need a few fields eg. only the country name you can specify a field argument with the names of the fields you want, if you combine this with the CSV output format you will get very clean results with only the data you need!

### To get full JSON responses for further processing

This is the default output format, so you could omit the `--format JSON`

```
ipdata batch my_ip_backlog.csv --output geolocation_results.json --format JSON
```

### Batch lookup with output to CSV file

```
ipdata batch my_ip_backlog.csv --output results.csv --output-format CSV --fields ip --fields country_code
```

The `--fields` option is required to use CSV output.

#### Example Results

```csv
# ip,country_code
107.175.75.83,US
35.155.95.229,US
13.0.0.164,US
209.248.120.14,US
142.0.202.238,US
...
```

### Available Fields

A list of all the fields returned by the API is maintained at [Response Fields](https://docs.ipdata.co/api-reference/response-fields)

## Geofeed tools

Geofeed publishers can use the `ipdata validate` command to validate their geofeeds before submission to ipdata. This will catch most but not all issues that might cause processing your geofeed to fail.

The validation closely follows https://datatracker.ietf.org/doc/html/draft-google-self-published-geofeeds-02 with one caveat, we expect the country field to be provided at the minimum.

You can provide either a url or a path to a local file.

```shell
ipdata validate https://example.com/geofeed.txt
```

or 

```shell
ipdata validate geofeed.txt
```

## Errors

A list of possible errors is available at [Status Codes](https://docs.ipdata.co/api-reference/status-codes)


## Tests

To run all tests

```shell
pytest
```
