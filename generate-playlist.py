#! /usr/bin/env python
from dataclasses import dataclass

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

credentials = SpotifyClientCredentials(
    client_id="",
    client_secret=""
)
spotify = spotipy.Spotify(auth_manager=credentials)


@dataclass
class Artist:
    name: str
    uri: str
    img: str

    def find_top_10_track_ids(self, desired_tempo=180):
        json = spotify.artist_top_tracks(self.uri)["tracks"]
        track_ids = [x['id'] for x in json]
        return filter_matching_bpm(track_ids, desired_tempo)


def filter_matching_bpm(track_ids, desired_tempo):
    tempi = spotify.audio_features(tracks=track_ids)
    return [track['id'] for track in tempi if is_good_tempo(track['tempo'], desired_tempo)]


def is_good_tempo(actual_tempo, desired_tempo):
    treshold = 2
    lower = desired_tempo - treshold
    upper = desired_tempo + treshold
    return ((lower < actual_tempo < upper) or
            (lower < actual_tempo * 2 < upper) or
            (lower < actual_tempo / 2 < upper))


def find_artist(desired_artist):
    desired_artist_results = spotify.search(q="artist:" + desired_artist, type="artist")
    artist = desired_artist_results["artists"]["items"][0]
    return Artist(
        artist['name'],
        artist["uri"],
        artist["images"][0]["url"]
    )


def run():
    root_artist = find_artist("eminem")
    root_artist.find_top_10_track_ids(170)


run()
