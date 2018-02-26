#!/usr/bin/python
"""
	This app is for testing purposes.
	Please write your own if you want to use the minecraft client libraries provided.
"""

from clientforge import MinecraftClientForge
from authmojang import MojangAuthentication
import os
import getpass
import uuid
import json
from pathlib import Path

auth_data = {
	"client_id": str(uuid.uuid4()),
	"access_token": None,
	"uuid": None,
	"player_name": None
}

if not os.path.exists('client.json'):
	with open('client.json', 'w') as fp:
		json.dump(auth_data, fp)
else:
	with open('client.json', 'r') as fp:
		fdata = json.load(fp)

		for k, i in auth_data.items():
			if not k in fdata:
				fdata[k] = i

		auth_data = fdata

def propmt():
	username = input('Username: ')
	password = getpass.getpass('Password for %s: ' % username)

	return MojangAuthentication(auth_data['client_id'], username, password)

def authstart():
	authenticated = False

	if not auth_data['access_token']:
		auth = propmt()
		authenticated = auth.authenticate()

		auth_data['access_token'] = auth.access_token
		auth_data['uuid'] = auth.uuid
		auth_data['player_name'] = auth.player_name
	else:
		auth = MojangAuthentication(auth_data['client_id'], None, None, auth_data['access_token'])
		authenticated = auth.refresh()

		if not authenticated:
			auth_data['access_token'] = None
			authstart()
			return

		auth_data['access_token'] = auth.access_token
		auth_data['uuid'] = auth.uuid
		auth_data['player_name'] = auth.player_name

	if authenticated:
		client = MinecraftClient(os.path.join(Path.home(), '.pymclaunch'), '1.12.2', 'Testing', auth)
		client.init_mc()

	with open('client.json', 'w') as fp:
		json.dump(auth_data, fp)

#authstart()

client = MinecraftClientForge(os.path.join(Path.home(), '.pymclaunch'), '1.12.2', 'forge-14.23.2.2619', 'Testing-Forge', 
	MojangAuthentication(auth_data['client_id'], None))

client.install_forge()

client.init_mc()
