import requests
import json

server = 'https://authserver.mojang.com'

class MojangAuthentication(object):
    """Authenticate against Mojang servers"""
    def __init__(self, clientToken, username, password=None, accessToken = None):
        super(MojangAuthentication, self).__init__()
        self.username = username
        self.password = password

        self.uuid = None
        self.player_name = "DemoUser"
        self.access_token = accessToken

        self.client_token = clientToken

    def authenticate(self, password = None):
        if not self.password and not password:
            if self.access_token:
                return self.validate()

            raise ValueError('Missing password field!')

        if not password:
            password = self.password

        payload = {
            "agent": {
                "name": "Minecraft",
                "version": 1
            },
            "username": self.username,
            "password": password,
            "clientToken": self.client_token,
            "requestUser": True
        }

        r = requests.post(server + '/authenticate', data=json.dumps(payload))

        if r.status_code == 200:
            json_data = r.json()

            if not 'selectedProfile' in json_data:
                raise ValueError('No profile found!')

            self.access_token = json_data['accessToken']
            self.player_name = json_data['selectedProfile']['name']
            self.uuid = json_data['selectedProfile']['id']
            
            print('Successful authentication as %s!' % (self.player_name))

            return True

        err = r.json()
        print('%s: %s' % (err['error'], err['errorMessage']))
        return False

    def validate(self):
        if not self.access_token:
            raise Exception('No access token specified!')

        payload = {
            "clientToken": self.client_token,
            "accessToken": self.access_token
        }

        r = requests.post(server + '/validate', data=json.dumps(payload))

        if r.status_code == 204:
            return True

        return False

    def refresh(self):
        if not self.access_token:
            raise Exception('No access token specified!')

        payload = {
            "agent": {
                "name": "Minecraft",
                "version": 1
            },
            "clientToken": self.client_token,
            "accessToken": self.access_token,
            "requestUser": True
        }

        r = requests.post(server + '/refresh', data=json.dumps(payload))

        if r.status_code == 200:
            json_data = r.json()

            if not 'selectedProfile' in json_data:
                raise ValueError('No profile found!')

            self.access_token = json_data['accessToken']
            self.player_name = json_data['selectedProfile']['name']
            self.uuid = json_data['selectedProfile']['id']
            
            print('Successfully refreshed %s\'s session!' % (self.player_name))

            return True

        err = r.json()
        print('%s: %s' % (err['error'], err['errorMessage']))
        return False

    def invalidate(self):
        if not self.access_token:
            raise Exception('No access token specified!')

        payload = {
            "clientToken": self.client_token,
            "accessToken": self.access_token
        }

        r = requests.post(server + '/invalidate', data=json.dumps(payload))

        if r.status_code == 204:
            self.access_token = None
            self.uuid = None

            return True

        return False
