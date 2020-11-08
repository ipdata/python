"""Call the https://api.ipdata.co API from Python."""

import ipaddress
import requests


class APIKeyNotSet(Exception):
    pass


class IncompatibleParameters(Exception):
    pass


class IPData:
    base_url = 'https://api.ipdata.co/'
    bulk_url = 'https://api.ipdata.co/bulk'
    valid_fields = {'ip', 'is_eu', 'city', 'region', 'region_code', 'country_name', 'country_code', 'continent_name',
                    'continent_code', 'latitude', 'longitude', 'asn', 'postal', 'calling_code', 'flag',
                    'emoji_flag', 'emoji_unicode', 'carrier', 'languages', 'currency', 'time_zone', 'threat', 'count',
                    'status'}

    def __init__(self, api_key):
        if not api_key:
            raise APIKeyNotSet("Missing API Key")
        self.api_key = api_key
        self.headers = {'user-agent': 'ipdata-pypi'}

    def _validate_fields(self, select_field=None, fields=None):
        if fields is None:
            fields = []

        if select_field and select_field not in self.valid_fields:
            raise ValueError(f"{select_field} is not a valid field.")
        if fields:
            if not isinstance(fields, list):
                raise ValueError('"fields" should be a list.')
            for field in fields:
                if field not in self.valid_fields:
                    raise ValueError(f"{field} is not a valid field.")

    def _validate_ip_address(self, ip):
        try:
            ipaddress.ip_address(ip)
        except Exception:
            raise
        if ipaddress.ip_address(ip).is_private:
            raise ValueError(f"{ip} is a private IP Address")

    def lookup(self, ip=None, select_field=None, fields=None):
        if fields is None:
            fields = []

        query = ""
        query_params = {'api-key': self.api_key}
        if ip:
            self._validate_ip_address(ip)
            query += f"{ip}/"
        if select_field and fields:
            raise IncompatibleParameters(
                "The \"select_field\" and \"fields\" parameters cannot be used at the same time.")
        if select_field:
            self._validate_fields(select_field=select_field)
            query += f"{select_field}/"
        if fields:
            self._validate_fields(fields=fields)
            query_params['fields'] = ','.join(fields)
        response = requests.get(f"{self.base_url}{query}", headers=self.headers, params=query_params)
        status_code = response.status_code
        if select_field and status_code == 200:
            try:
                response = {select_field: response.json(), 'status': status_code}
                return response
            except Exception:
                response = {select_field: response.text, 'status': status_code}
                return response
        response = response.json()
        response['status'] = status_code
        return response

    def bulk_lookup(self, ips=None, fields=None):
        if ips is None:
            ips = []
        if fields is None:
            fields = []

        query_params = {'api-key': self.api_key}
        if len(ips) < 2:
            raise ValueError('Bulk Lookup requires more than 1 IP Address in the payload.')
        for ip in ips:
            self._validate_ip_address(ip)
        if fields:
            self._validate_fields(fields=fields)
            query_params['fields'] = ','.join(fields)
        response = requests.post(f"{self.bulk_url}", headers=self.headers, params=query_params, json=ips)
        status_code = response.status_code
        if not status_code == 200:
            response = response.json()
            response['status'] = status_code
            return response
        response = {'responses': response.json(), 'status': status_code}
        return response
