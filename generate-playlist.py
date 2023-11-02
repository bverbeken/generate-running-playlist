#! /usr/bin/env python

from dataclasses import dataclass

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from spotify_credentials import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

credentials = SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
)
spotify = spotipy.Spotify(auth_manager=credentials)


@dataclass
class TrackList:
    tracks = []

    def add(self, tracks):
        self.tracks.extend(tracks)

    def __iter__(self):
        return self.tracks.__iter__()


@dataclass
class Track:
    id: str
    name: str
    artist: str


@dataclass
class Artist:
    name: str
    uri: str
    img: str
    top_tracks = None
    related_artists = None

    def get_top_tracks(self):
        if self.top_tracks is None:
            json = spotify.artist_top_tracks(self.uri)["tracks"]
            self.top_tracks = [Track(track['id'], track['name'], track['artists'][0]['name']) for track in json]
        return self.top_tracks

    def get_top_tracks_with_bpm(self, bpm):
        tracks = self.get_top_tracks()
        return filter_matching_bpm(tracks, bpm)

    def get_related_artists(self):
        if self.related_artists is None:
            related_artists = spotify.artist_related_artists(self.uri)["artists"]
            self.related_artists = [Artist(x['name'], x['uri'], x['images'][0]["url"]) for x in related_artists]
        return self.related_artists

    def get_related_artists_top_tracks(self, bpm):
        tracks = []
        for artist in self.get_related_artists():
            tracks.extend(artist.get_top_tracks_with_bpm(bpm))
        return tracks


def filter_matching_bpm(tracks, desired_tempo):
    tempi = spotify.audio_features(tracks=[track.id for track in tracks])
    return [track for track, tempo in zip(tracks, tempi) if is_good_tempo(tempo['tempo'], desired_tempo)]


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
    artist = find_artist("eminem")
    bpm = 170
    tracks = TrackList()
    tracks.add(artist.get_top_tracks_with_bpm(bpm))
    tracks.add(artist.get_related_artists_top_tracks(bpm))
    tracks.add(artist.get_recommended_tracks_from_top_tracks(bpm))
    for track in tracks:
        print(track)
    # tracks = artist.get_top_tracks_with_bpm(bpm)
    # related_artist_tracks = artist.find_related_artists_tracks(bpm)


run()
