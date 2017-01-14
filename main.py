import click
import urllib
import base64
import requests
import json
import secret # local file that includes API keys
from bs4 import BeautifulSoup
from flask import Flask, request, redirect, render_template, session
app = Flask(__name__)


# All spotify authentication code from https://github.com/drshrey/spotify-flask-auth-example/blob/master/main.py


# Spotify URLS
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
S_API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, S_API_VERSION)

# Musixmatch URLS
M_BASE_URL = "http://api.musixmatch.com/ws"
M_API_VERSION = "1.1"
M_API_URL = "{}/{}".format(M_BASE_URL, M_API_VERSION)

# Genius URLS
G_API_URL = "http://api.genius.com"

# Spotify API keys
S_ID = secret.S_ID
S_SECRET = secret.S_SECRET

# Musixmatch API keys
M_KEY = secret.M_KEY

# Genius API keys
G_KEY = secret.G_KEY
G_SECRET = secret.G_SECRET
G_TOKEN = secret.G_TOKEN

# Session key
app.secret_key = secret.SESSION_SECRET


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
  session['authorization_header'] = {"Authorization":"Bearer {}".format(access_token)}

  # Get user's name
  user_profile_api_endpoint = "{}/me".format(SPOTIFY_API_URL)
  profile_response = requests.get(user_profile_api_endpoint, headers=session['authorization_header'])
  profile_data = json.loads(profile_response.text)
  session['user_id'] = profile_data["id"]

  # Get user playlist data
  playlist_api_endpoint = "{}/playlists".format(profile_data["href"])
  playlists_response = requests.get(playlist_api_endpoint, headers=session['authorization_header'])
  playlist_data = json.loads(playlists_response.text)

  return render_template('welcome.html', name=profile_data["display_name"], playlists=playlist_data["items"], data=playlist_data)


@app.route("/callback/<playlist_id>")
def search(playlist_id):
  tracks = []

  # Get list of playlist's tracks
  playlist_tracks_api_endpoint = "{}/users/{}/playlists/{}/tracks".format(SPOTIFY_API_URL, session['user_id'], playlist_id)
  playlist_tracks_response = requests.get(playlist_tracks_api_endpoint, headers=session['authorization_header'])
  playlist_tracks_data = json.loads(playlist_tracks_response.text)


  # Can only display 100 tracks at a time
  # So may need to make call multiple times
  while True:
    # Add track names and artist to dict
    for track in playlist_tracks_data["items"]:
      track_name = track["track"]["name"]
      artist_name = track["track"]["artists"][0]["name"]
      tracks.append([track_name, artist_name, "", ""])

    # See if there are more tracks
    if playlist_tracks_data["next"] == None:
      break

    # Make next call
    playlist_tracks_response = requests.get(playlist_tracks_data["next"], headers=session['authorization_header'])
    playlist_tracks_data = json.loads(playlist_tracks_response.text)
  

  # Authenticate Genius
  session['g_authorization_header'] = {"Authorization":"Bearer {}".format(G_TOKEN)}


  # Get lyrics to each song
  for track in tracks:
    lyrics_id_api_endpoint = "{}/search".format(G_API_URL)
    lyrics_id_response = requests.get(lyrics_id_api_endpoint, params={'q': "{} {}".format(track[0], track[1])}, headers=session['g_authorization_header'])
    lyrics_id_data = json.loads(lyrics_id_response.text)
    track_url = lyrics_id_data["response"]["hits"][0]["result"]["url"]


    # Scrape lyrics
    # Credit: http://www.jw.pe/blog/post/quantifying-sufjan-stevens-with-the-genius-api-and-nltk/
    lyrics_response = requests.get(track_url)
    html = lyrics_response.text

    soup = BeautifulSoup(html, 'html.parser')

    lyrics = soup.find(name="lyrics")
    lyrics.script

    lyrics_text = " / ".join([lyric for lyric in lyrics.stripped_strings])
    track[2] = lyrics_text


  return render_template('search.html', tracks=tracks, response=playlist_tracks_response)