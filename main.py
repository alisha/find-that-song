from __future__ import print_function
import click
import urllib
import base64
import requests
import requests_cache
import json
import secret # local file that includes API keys
from bs4 import BeautifulSoup
import sys
import regex
from flask import Flask, request, redirect, render_template, session
app = Flask(__name__)


# All spotify authentication code from https://github.com/drshrey/spotify-flask-auth-example/blob/master/main.py

# Spotify URLS
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
S_API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, S_API_VERSION)

# Genius URLS
G_API_URL = "http://api.genius.com"

# Spotify API keys
S_ID = secret.S_ID
S_SECRET = secret.S_SECRET

# Genius API keys
G_KEY = secret.G_KEY
G_SECRET = secret.G_SECRET
G_TOKEN = secret.G_TOKEN

# Session key
app.secret_key = secret.SESSION_SECRET


# Server-side Parameters
CLIENT_SIDE_URL = "http://127.0.0.1"
PORT = 5000
REDIRECT_URI = "{}:{}".format(CLIENT_SIDE_URL, PORT)
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


requests_cache.install_cache()

# Spotify authentication mostly based on: https://github.com/drshrey/spotify-flask-auth-example
@app.route('/', methods=['GET', 'POST'])
def home():
  # User has logged in, now store the authorization header
  if request.args and request.args['code']:
    auth_token = request.args['code']
    code_payload = {
      "grant_type": "authorization_code",
      "code": str(auth_token),
      "redirect_uri": REDIRECT_URI
    }
    base64encoded = base64.b64encode("{}:{}".format(S_ID, S_SECRET))
    headers = {"Authorization": "Basic {}".format(base64encoded)}
    post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload, headers=headers)

    response_data = json.loads(post_request.text)
    access_token = response_data["access_token"]
    refresh_token = response_data["refresh_token"]
    session['refresh_token'] = refresh_token
    token_type = response_data["token_type"]
    expires_in = response_data["expires_in"]

    session['authorization_header'] = {"Authorization":"Bearer {}".format(access_token)}

  # Need to authenticate user
  if 'authorization_header' not in session:
    url_args = "&".join(["{}={}".format(key,urllib.quote(val)) for key,val in auth_query_parameters.iteritems()])
    auth_url = "{}/?{}".format(SPOTIFY_AUTH_URL, url_args)
    return redirect(auth_url)

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


@app.route("/search")
def search():
  tracks = []

  # Access URL parameters
  playlist_id = request.args.get('playlist_id', '')
  query = request.args.get('query', '')

  # Get list of playlist's tracks
  playlist_tracks_api_endpoint = "{}/users/{}/playlists/{}/tracks".format(SPOTIFY_API_URL, session['user_id'], playlist_id)
  playlist_tracks_response = requests.get(playlist_tracks_api_endpoint, headers=session['authorization_header'])
  playlist_tracks_data = json.loads(playlist_tracks_response.text)

  # Access token has expired
  if 'error' in playlist_tracks_data and playlist_tracks_data['error']['status'] == 401 and playlist_tracks_data['error']['message'] == 'The access token expired':
    # Refresh access token
    post_request = requests.post(SPOTIFY_TOKEN_URL, headers=session['authorization_header'], grant_type="refresh_token", refresh_token=session['refresh_token'])
    response_data = json.loads(post_request.text)
    access_token = response_data['access_token']
    session['authorization_header'] = {"Authorization":"Bearer {}".format(access_token)}

    # Try again
    playlist_tracks_response = requests.get(playlist_tracks_api_endpoint, headers=session['authorization_header'])
    playlist_tracks_data = json.loads(playlist_tracks_response.text)
  
  # Can only display 100 tracks at a time
  # So may need to make call multiple times
  while True:
    # Add track names and artist to dict
    for track in playlist_tracks_data["items"]:
      uri = track["track"]["uri"]
      track_name = track["track"]["name"]
      artist_name = track["track"]["artists"][0]["name"]
      tracks.append([uri, track_name, artist_name, "", ""])

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
    # Song info
    song_name = track[1].encode('utf-8')
    # Remove anything in parentheses from song name
    # Yields more accurate search results
    paren_index = song_name.find('(')
    if paren_index != -1:
      song_name = song_name[:paren_index]
    artist = track[2].encode('utf-8')

    # Scrape lyrics
    # Credit: http://www.jw.pe/blog/post/quantifying-sufjan-stevens-with-the-genius-api-and-nltk/
    lyrics_id_api_endpoint = "{}/search".format(G_API_URL)
    lyrics_id_response = requests.get(lyrics_id_api_endpoint, params={'q': "{} {}".format(song_name, artist)}, headers=session['g_authorization_header'])
    lyrics_id_data = json.loads(lyrics_id_response.text)
    
    # Valid response, found lyrics
    if lyrics_id_data["meta"]["status"] == 200 and len(lyrics_id_data["response"]["hits"]) > 0 and lyrics_id_data["response"]["hits"][0]["result"]["primary_artist"]["name"].encode('utf-8').lower() == artist.lower():
      track_url = lyrics_id_data["response"]["hits"][0]["result"]["url"]
      lyrics_response = requests.get(track_url)

      soup = BeautifulSoup(lyrics_response.text, 'html.parser')
      lyrics = soup.find("div", { "class" : "lyrics" })
      lyrics.script
      lyrics_text = " / ".join([lyric for lyric in lyrics.stripped_strings])

      track[3] = lyrics_text

    # No lyrics
    else:
      track[3] = ""


  # Search lyrics with regex
  regex_query = regex.compile('(' + query + '){e<=' + str(len(query)/2) + '}', regex.IGNORECASE | regex.BESTMATCH)
  matches = []

  for track in tracks:
    search_obj = regex_query.search(regex.escape(track[3]))

    if search_obj:
      if search_obj.fuzzy_counts:
        matches.append([track[0], track[1], track[2], track[3], search_obj.fuzzy_counts[0]])
      else:
        # Perfect match; 0 errors
        matches.append([track[0], track[1], track[2], track[3], 0])

  # Sort by number of errors
  matches.sort(key=lambda match: match[4])

  best_matches = matches[:6]

  return render_template('search.html', matches=best_matches, query=query)