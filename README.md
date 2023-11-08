A script to create a Spotify playlist with songs at a certain bpm.

# Usage

### Step 1
First, create a spotify app on https://developer.spotify.com/dashboard.
redirect URL should be 'http://localhost:29292' (or any other port you fancy).
This script will open a temp http server on that port.

### Step 2
Then, create a file called `spotify_credentials.py` in the root, i.e. next to `generate-playlist.py`, containing:

```
SPOTIFY_CLIENT_ID="YOUR_CLIENT_ID"
SPOTIFY_CLIENT_SECRET="YOUR_CLIENT_SECRET"
SPOTIFY_REDIRECT_PORT = 29292
```

### Step 3
Specify the artist and bpm in generate-playlist.py

### Step 4
Run ./generate_playlist.py
