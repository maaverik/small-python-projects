import json
import os
import pickle
from typing import Dict, List

import googleapiclient.discovery
import googleapiclient.errors
import requests
import youtube_dl
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow, InstalledAppFlow

# Prerequisites
#
# Create a project on google developer console site
# Enable the Youtube Data API v3
# Create OAuth credentials for web server - https://console.cloud.google.com/apis/credentials?project=<PROJECT>
# Add your email id in the consent section as a test user - https://console.cloud.google.com/apis/credentials/consent?project=<PROJECT>
#
# Set up a spotify dev account token at https://developer.spotify.com/console/post-playlists/?user_id=&body=%7B%22name%22%3A%22New%20Playlist%22%2C%22description%22%3A%22New%20playlist%20description%22%2C%22public%22%3Afalse%7D

spotify_token = 'YOUR SPOTIFY TOKEN'
# https://www.spotify.com/us/account/overview/
spotify_user_id = 'YOUR SPOTIFY USERNAME'


def get_yt_credentials() -> Flow.credentials:
    """Store google credentials locally instead of having to keep logging in again and again"""
    credentials = None
    # token.pickle stores the user's credentials from previously successful logins
    if os.path.exists('token.pickle'):
        print('Loading Credentials From File...')
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)

    # If there are no valid credentials available, then either refresh the token or log in.
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            print('Refreshing Access Token...')
            credentials.refresh(Request())
        else:
            print('Fetching New Tokens...')
            flow = InstalledAppFlow.from_client_secrets_file(
                # get this from the google dev console and rename to client_secret.json
                'client_secret.json',
                scopes=[
                    'https://www.googleapis.com/auth/youtube.readonly'
                ]
            )

            flow.run_local_server(port=8080, prompt='consent',
                                  authorization_prompt_message='')
            credentials = flow.credentials

            # Save the credentials for the next run
            with open('token.pickle', 'wb') as f:
                print('Saving Credentials for Future Use...')
                pickle.dump(credentials, f)
    return credentials


def extract_songs_data_from_yt(data: Dict) -> List:
    """Fetch song name from Youtube"""
    url = "https://www.youtube.com/watch?v="
    info = []
    for i in range(len(data["items"])):
        try:
            video_url = url+str(data["items"][i]["snippet"]
                                ['resourceId']['videoId'])
            details = youtube_dl.YoutubeDL(
                {}).extract_info(video_url, download=False)
            if 'track' in details and 'artist' in details:
                track, artist = details['track'], details['artist']
                info.append((track, artist))
        except Exception as e:
            # only songs have track and artist, so automatically filters out songs
            print(f'Something went wrong for {video_url}, skipping')
            print(e)
    return info


def get_yt_playlist_data(credentials: Flow.credentials, pageToken: str = None) -> Dict:
    api_service_name = "youtube"
    api_version = "v3"

    youtube = googleapiclient.discovery.build(api_service_name,
                                              api_version,
                                              credentials=credentials)
    request = youtube.playlistItems().list(
        part="snippet",
        playlistId="LL",    # LL => liked videos
        maxResults=50,
        pageToken=pageToken
    )
    response = request.execute()

    return response


def create_new_spotify_playlist() -> Dict:
    """Create A New Playlist"""
    request_body = json.dumps(
        {
            "name": "NEW PLAYLIST NAME",
            "description": "DESCRIPTION",
            "public": False,
        }
    )

    query = "https://api.spotify.com/v1/users/{}/playlists".format(
        spotify_user_id)
    response = requests.post(
        query,
        data=request_body,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(spotify_token),
        },
    )
    response = response.json()
    return response["id"]


def get_spotify_uri(track: str, artist: str):
    """Search For the Song"""

    query = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track".format(
        track,
        artist
    )
    response = requests.get(
        query,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(spotify_token)
        }
    ).json()
    try:
        songs = response["tracks"]["items"]
        url = songs[0]["uri"]
        return url
    except Exception as e:
        print(f'Something went wrong for {track}, skipping')
        print(e)


def add_songs_to_spotify(playlist_id: str, urls: List):
    """Add all songs into the new Spotify playlist"""

    while urls:
        request_data = json.dumps(urls[:100])   # 100 at a time is the limit

        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(
            playlist_id)

        response = requests.post(
            query,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        print(response.json())
        urls = urls[100:]

    return response


def main():
    try:
        credentials = get_yt_credentials()
        songs_data = []
        playlist_data = get_yt_playlist_data(credentials)
        while playlist_data.get('nextPageToken'):   # pagination
            songs_data.extend(extract_songs_data_from_yt(playlist_data))
            playlist_data = get_yt_playlist_data(
                credentials, playlist_data['nextPageToken'])
        playlist_id = create_new_spotify_playlist()
        song_uris = [get_spotify_uri(track, artist)
                     for track, artist in songs_data]
        song_uris = [uri for uri in song_uris if uri]
        add_songs_to_spotify(playlist_id, song_uris)
    except Exception as e:
        print(f'Something went wrong')
        print(e)


if __name__ == "__main__":
    main()
