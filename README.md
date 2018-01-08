# Find That Song

This is a web app to help you figure out what song is stuck in your head, if you know which Spotify playlist it's in. Just log in with your Spotify account, type in whatever lyrics you can remember, choose the playlist, and finally find that song.

Lyrics are scraped from Genius. While requests are cached, large playlists may take time to scan.

## Getting Started

### Prerequisites

Create an app on the Spotify Developers site and get a client ID. Create a `secret.py` file with the following:
```
S_ID = "" // your client ID
S_SECRET = "" // your client secret
```


Run the following to install required modules:
```
pip install -r requirements.txt
```

### Installing

Run the following to get a developer environment up:
```
FLASK_APP=main.py FLASK_DEBUG=1 python -m flask run
```

## License

This project is licensed under the MIT License - see the [LICENSE.md](https://github.com/alisha/find-that-song/blob/master/LICENSE.md) file for details.