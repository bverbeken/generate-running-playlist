#! /usr/bin/env python

source = "Eminem"
tempo_in_bpm = 170

# ------------------------------------------------------------------------------------------------------------

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
        return self

    def __iter__(self):
        return iter(self.tracks)


@dataclass
class Track:
    id: str
    name: str
    source: str


@dataclass
class Artist:
    name: str
    uri: str
    img: str
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
            self.related_artists = [Artist(x['name'], x['uri'], x['images'][0]["url"]) for x in related_artists]
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

    def fits_filters(af): (
            has_bpm(af['tempo'], bpm) and
            has_four_four_time(af['time_signature'])
    )

    return [track for track, tempo in zip(tracks, combined_results) if fits_filters]


def has_four_four_time(time_signature):
    return time_signature == 4


def has_bpm(actual_tempo, wanted_tempo):
    treshold = 2
    lower = wanted_tempo - treshold
    upper = wanted_tempo + treshold
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
    artist = find_artist(source)
    tracks = (TrackList()
              .add(artist.list_top_tracks(tempo_in_bpm))
              .add(artist.list_recommended_tracks(tempo_in_bpm))
              .add(artist.list_related_artist_top_tracks(tempo_in_bpm))
              )
    for track in tracks:
        print(track)


run()
