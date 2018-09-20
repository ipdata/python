"""Call the https://api.ipdata.co API from Python."""
import requests, json

class ipdata:
    base_url = 'https://api.ipdata.co/{ip}/{language}/?api-key={apikey}'
    def __init__(self, apikey=None,language='en'):
        self.apikey = apikey
        self.language = language
        self.headers = {'user-agent': 'ipdata-pypi/2.4'}
    def lookup(self, ip):
        r = requests.get(self.base_url.format(ip=ip, language=self.language, apikey=self.apikey), headers=self.headers)
        if r.status_code==200:
            return {'status':r.status_code, 'response':r.json()}
        return {'status':r.status_code, 'response':r.text}

