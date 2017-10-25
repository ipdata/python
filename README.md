# Getting Started

This repo provides a Python client for the [https://ipdata.co](ipdata.co) Free Geolocation API.

## Installation

Run

```
pip install ipdata
```

## Examples

```
ip = ipdata()
res = ip.lookup('1.1.1.1')
# {u'calling_code': u'61', u'city': u'Research', u'organisation': u'', u'latitude': -37.7, u'ip': u'1.1.1.1', u'region': u'Victoria', u'time_zone': u'Australia/Melbourne', u'continent_code': u'OC', u'currency': u'AUD', u'continent_name': u'Oceania', u'flag': u'https://ipdata.co/flags/au.png', u'longitude': 145.1833, u'country_code': u'AU', u'country_name': u'Australia', u'postal': u'3095', u'asn': u''}
```

To get a specific field, do

```
country = ip.lookup('1.1.1.1')['country_name]
u'country_name': u'Australia'
```

### Using API keys

```
apikey = 'myapikey'
ip = ipdata(apikey=apikey)
res = ip.lookup('1.1.1.1')
```