"""Call the https://api.ipdata.co API from Python."""
import requests, json

class ipdata:
    base_url = 'https://api.ipdata.co/{ip}/{language}'
    def __init__(self, apikey=None,language='en'):
        self.apikey = apikey
        self.language = language
        self.headers = {'user-agent': 'ipdata-pypi/2.3'}
    def lookup(self, ip):
        try:
            if self.apikey:
                self.headers ['api-key'] = self.apikey
            r = requests.get(self.base_url.format(ip=ip, language=self.language), headers=self.headers)
            if r.status_code==200:
                return {'status':r.status_code, 'response':r.json()}
            return {'status':r.status_code, 'response':r.text}
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            print(e)
            sys.exit(1)