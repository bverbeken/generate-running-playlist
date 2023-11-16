#! /usr/bin/env python
import http.server
import random
import socketserver
import threading
import time
import webbrowser
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from spotify_credentials import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_PORT as PORT

# ------------------------------------------------------------------------------------------------------------
# Input parameters

source = "Eminem"
tempo_in_bpm = 180
max_playlist_size = 100

# ------------------------------------------------------------------------------------------------------------

auth_manager = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=f"http://localhost:{PORT}",
    scope='playlist-modify-public playlist-modify-private',
    open_browser=False
)

auth_code = None


def fetch_authentication_token():
    def start_callback_server():
        class SpotifyAuthHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                global auth_code
                url = urlparse(self.path)
                query_params = parse_qs(url.query)

                if 'code' in query_params:
                    auth_code = query_params['code'][0]
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b"Authentication successful! You can close this window.")
                else:
                    self.send_response(400)
                    self.send_header('Content-Type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b"Authentication failed: 'code' parameter not found in the query string.")
                threading.Thread(target=httpd.shutdown, daemon=True).start()

        # Create and start the HTTP server
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", PORT), SpotifyAuthHandler) as httpd:
            httpd.serve_forever()

    auth_url = auth_manager.get_authorize_url()
    webbrowser.open(auth_url)
    start_callback_server()
    if auth_code:
        return auth_manager.get_access_token(auth_code, as_dict=False)
    else:
        error_and_exit("Failed to retrieve authentication code.")


def error_and_exit(error_msg):
    red = '\033[91m'
    endc = '\033[0m'
    print(red + error_msg + endc)
    exit(1)


def get_user_id():
    response = requests.get(
        url="https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()['id']


@dataclass
class TrackList:
    tracks = []

    def add(self, new_tracks):
        self.tracks.extend(new_tracks)
        while len(self.tracks) > max_playlist_size:
            self.tracks.pop(random.randint(0, len(self.tracks) - 1))
        return self

    def __iter__(self):
        return iter(self.tracks)

    def __len__(self):
        return len(self.tracks)

    def create_playlist(self, name):
        user_id = get_user_id()
        playlist_id = spotify.user_playlist_create(user_id, name)["id"]
        spotify.playlist_add_items(playlist_id, self.track_ids())

    def track_ids(self):
        return [track.id for track in self.tracks]


@dataclass
class Track:
    id: str
    name: str
    source: str


@dataclass
class Artist:
    name: str
    uri: str
    top_tracks = None
    related_artists = None

    def list_top_tracks(self, bpm):
        tracks = self._get_top_tracks()
        return filter_matching_bpm(tracks, bpm)

    def list_related_artist_top_tracks(self, bpm):
        tracks = []
        for artist in self._get_related_artists():
            tracks.extend(artist.list_top_tracks(bpm))
        return tracks

    def list_recommended_tracks(self, bpm):
        tracks = self._get_recommended_tracks_from_top_tracks()
        return filter_matching_bpm(tracks, bpm)

    def _get_top_tracks(self):
        if self.top_tracks is None:
            json = spotify.artist_top_tracks(self.uri)["tracks"]
            self.top_tracks = [Track(track['id'], track['name'], track['artists'][0]['name']) for track in json]
        return self.top_tracks

    def _get_related_artists(self):
        if self.related_artists is None:
            related_artists = spotify.artist_related_artists(self.uri)["artists"]
            self.related_artists = [Artist(x['name'], x['uri']) for x in related_artists]
        return self.related_artists

    def _get_recommended_tracks_from_top_tracks(self):
        top_track_ids = [track.id for track in self._get_top_tracks()]
        recommendations = get_spotify_recommendations(top_track_ids)
        return recommendations


def chunked_array(array, size):
    return [array[i:i + size] for i in range(0, len(array), size)]


def get_spotify_recommendations(track_ids):
    chunks = chunked_array(track_ids, 3)
    results = []
    for chunk in chunks:
        tracks = spotify.recommendations(seed_tracks=chunk, limit=100)["tracks"]
        results.append(Track(track['id'], track['name'], track['artists'][0]['name']) for track in tracks)
    combined_results = [item for sublist in results for item in sublist]
    return combined_results


def filter_matching_bpm(tracks, bpm):
    track_ids = [track.id for track in tracks]
    chunked_track_ids = chunked_array(track_ids, 10)
    results = []
    for chunk in chunked_track_ids:
        audio_features = spotify.audio_features(tracks=chunk)
        results.append(audio_features)
    combined_results = [item for sublist in results for item in sublist]

    def fits_filters(af):
        return (
                has_bpm(af['tempo'], bpm) and
                has_good_signature_for_running(af['time_signature'])
        )

    mapped_results = [track for track, tempo in zip(tracks, combined_results) if fits_filters(tempo)]
    return mapped_results


def has_good_signature_for_running(time_signature):
    return time_signature == 4 or time_signature == 2


def has_bpm(actual, wanted):
    treshold = 2
    lower = wanted - treshold
    upper = wanted + treshold
    return ((lower < actual < upper) or
            (lower < actual * 2 < upper) or
            (lower < actual / 2 < upper))


def find_artist(desired_artist):
    desired_artist_results = spotify.search(q="artist:" + desired_artist, type="artist")
    artist = desired_artist_results["artists"]["items"][0]
    return Artist(
        artist['name'],
        artist["uri"]
    )


def run():
    artist = find_artist(source)
    track_list = (
        TrackList()
        .add(artist.list_top_tracks(tempo_in_bpm))
        .add(artist.list_recommended_tracks(tempo_in_bpm))
        .add(artist.list_related_artist_top_tracks(tempo_in_bpm))
    )
    track_list.create_playlist(f"GENERATED - {time.time()} - Based on artist: " + artist.name)


token = fetch_authentication_token()
spotify = spotipy.Spotify(auth=token)
run()
