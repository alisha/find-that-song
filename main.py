import click
import urllib
import base64
import requests
import json
import secret # local file that includes API keys
from flask import Flask, request, redirect, render_template
from flask_cli import FlaskCLI
app = Flask('myapp')
FlaskCLI(app)


# All spotify authentication code from https://github.com/drshrey/spotify-flask-auth-example/blob/master/main.py


# Spotify URLS
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)


# Spotify API keys
S_ID = secret.S_ID
S_SECRET = secret.S_SECRET

# Musixmatch API keys
#M_KEY = secret.M_KEY


# Server-side Parameters
CLIENT_SIDE_URL = "http://127.0.0.1"
PORT = 5000
REDIRECT_URI = "{}:{}/callback/q".format(CLIENT_SIDE_URL, PORT)
SCOPE = ""
STATE = ""
SHOW_DIALOG_bool = True
SHOW_DIALOG_str = str(SHOW_DIALOG_bool).lower()


auth_query_parameters = {
  "response_type": "code",
  "redirect_uri": REDIRECT_URI,
  "scope": "",
  "state": STATE,
  "show_dialog": SHOW_DIALOG_str,
  "client_id": S_ID
}


@app.route('/', methods=['GET', 'POST'])
def auth_spotify():
  url_args = "&".join(["{}={}".format(key,urllib.quote(val)) for key,val in auth_query_parameters.iteritems()])
  auth_url = "{}/?{}".format(SPOTIFY_AUTH_URL, url_args)
  return redirect(auth_url)


@app.route("/callback/q")
def callback():
  # Auth Step 4: Requests refresh and access tokens
  auth_token = request.args['code']
  code_payload = {
    "grant_type": "authorization_code",
    "code": str(auth_token),
    "redirect_uri": REDIRECT_URI
  }
  base64encoded = base64.b64encode("{}:{}".format(S_ID, S_SECRET))
  headers = {"Authorization": "Basic {}".format(base64encoded)}
  post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload, headers=headers)

  # Auth Step 5: Tokens are Returned to Application
  response_data = json.loads(post_request.text)
  access_token = response_data["access_token"]
  refresh_token = response_data["refresh_token"]
  token_type = response_data["token_type"]
  expires_in = response_data["expires_in"]

  # Auth Step 6: Use the access token to access Spotify API
  authorization_header = {"Authorization":"Bearer {}".format(access_token)}