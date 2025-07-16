import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from dotenv import load_dotenv
import os
import time

# Explicitly load .env from the script's directory to ensure it's always found.
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

class SpotifyAPI:
    def __init__(self, client_id, client_secret, redirect_uri, scope="playlist-modify-public user-library-read"):
        """
        Initializes the SpotifyAPI client with automatic retry logic.
        """
        # The retry config now uses the correct 'status_forcelist' parameter.
        retry_config = {
            'retries': 5,
            'status_forcelist': [429, 500, 502, 503, 504],
            # 'status_retry_forcelist': [429, 500, 502, 503, 504]
        }
        
        self.sp_user = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id,
                                                                  client_secret=client_secret,
                                                                  redirect_uri=redirect_uri,
                                                                  scope=scope), **retry_config)
        self.sp_public = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id,
                                                                                client_secret=client_secret), **retry_config)
        self.user_id = self.sp_user.me()['id']

    def _is_playlist_modifiable(self, playlist_id):
        """
        Checks if a playlist is modifiable (i.e., its name ends with '_sb').
        """
        playlist = self.sp_public.playlist(playlist_id, fields='name')
        return playlist['name'].endswith('_sb')

    def create_playlist(self, name, public=True, description=''):
        """
        Creates a new playlist. Ensures the playlist name has the '_sb' suffix.
        """
        if not name.endswith('_sb'):
            name += '_sb'
        return self.sp_user.user_playlist_create(self.user_id, name, public, description)

    def add_song_to_playlist(self, playlist_id, track_ids):
        """
        Adds one or more songs to a playlist, only if it's modifiable.
        """
        if not self._is_playlist_modifiable(playlist_id):
            print(f"Playlist (ID: {playlist_id}) is not modifiable. It must end with '_sb'.")
            return None
        if not isinstance(track_ids, list):
            track_ids = [track_ids]
        
        # Add tracks in chunks of 100 to avoid request size limits
        for i in range(0, len(track_ids), 100):
            chunk = track_ids[i:i+100]
            self.sp_user.playlist_add_items(playlist_id, chunk)
            time.sleep(0.5) # Add a small delay between chunk uploads
        return True

    def remove_song_from_playlist(self, playlist_id, track_ids):
        """
        Removes one or more songs from a playlist, only if it's modifiable.
        """
        if not self._is_playlist_modifiable(playlist_id):
            print(f"Playlist (ID: {playlist_id}) is not modifiable. It must end with '_sb'.")
            return None
        if not isinstance(track_ids, list):
            track_ids = [track_ids]
        
        # Remove tracks in chunks of 100
        for i in range(0, len(track_ids), 100):
            chunk = track_ids[i:i+100]
            self.sp_user.playlist_remove_all_occurrences_of_items(playlist_id, chunk)
            time.sleep(0.5)
        return True

    def delete_playlist(self, playlist_id):
        """
        Deletes a playlist, only if it's modifiable.
        """
        if not self._is_playlist_modifiable(playlist_id):
            print(f"Playlist (ID: {playlist_id}) is not modifiable. It must end with '_sb'.")
            return None
        return self.sp_user.current_user_unfollow_playlist(playlist_id)

    def reorder_playlist(self, playlist_id, sort_key='artist', reverse=False):
        """
        Reorders a playlist based on a specified key.
        Sort keys can be 'artist', 'album', 'name', 'added_at', 'popularity'.
        """
        if not self._is_playlist_modifiable(playlist_id):
            print(f"Playlist (ID: {playlist_id}) is not modifiable. It must end with '_sb'.")
            return None

        items = self.list_songs(playlist_id=playlist_id)
        
        def get_sort_value(item):
            track = item.get('track', {})
            if not track: return '' # Handle cases where track is None
            if sort_key == 'artist':
                return track.get('artists', [{}])[0].get('name', '')
            elif sort_key == 'album':
                return track.get('album', {}).get('name', '')
            elif sort_key == 'name':
                return track.get('name', '')
            elif sort_key == 'added_at':
                return item.get('added_at', '')
            elif sort_key == 'popularity':
                return track.get('popularity', 0)
            return ''

        items.sort(key=get_sort_value, reverse=reverse)
        
        track_uris = [item['track']['uri'] for item in items if item.get('track')]
        if not track_uris:
            return None

        # Re-ordering is done by replacing the first 100, then adding the rest.
        self.sp_user.playlist_replace_items(playlist_id, track_uris[:100])
        time.sleep(0.5)
        for i in range(100, len(track_uris), 100):
            chunk = track_uris[i:i+100]
            self.sp_user.playlist_add_items(playlist_id, chunk)
            time.sleep(0.5)
        return True

    def list_songs(self, playlist_id=None):
        """
        Lists song items from a specific playlist or from the user's "Liked Songs".
        Each item includes the track object and metadata like 'added_at'.
        """
        all_items = []
        if playlist_id:
            results = self.sp_user.playlist_items(playlist_id)
        else:
            results = self.sp_user.current_user_saved_tracks()

        while results:
            all_items.extend(results['items'])
            if results['next'] and hasattr(self.sp_user, 'next'):
                results = self.sp_user.next(results)
            else:
                results = None
        return all_items

    def get_song_genre(self, song_id):
        """
        Retrieves the genres of a song's primary artist.
        """
        track_info = self.sp_public.track(song_id)
        if not track_info or not track_info['artists']:
            return []
        
        artist_id = track_info['artists'][0]['id']
        artist_info = self.sp_public.artist(artist_id)
        return artist_info.get('genres', [])

    def list_available_genres(self):
        """
        Returns a list of all available genre seeds from Spotify.
        """
        return self.sp_public.recommendation_genre_seeds().get('genres', [])

    def get_song_metadata(self, song_id):
        """
        Retrieves metadata for a song.
        """
        return self.sp_public.track(song_id)

    def search_song(self, query, search_type='track', limit=10):
        """
        Searches for a song on Spotify.
        """
        return self.sp_public.search(q=query, type=search_type, limit=limit)

if __name__ == '__main__':
    # Example Usage:
    # Make sure you have a .env file with your credentials
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    REDIRECT_URI = os.getenv("REDIRECT_URI")

    if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
        print("Missing Spotify credentials in .env file")
    else:
        spotify_client = SpotifyAPI(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)

        # 1. List liked songs
        print("Your Liked Songs:")
        liked_songs = spotify_client.list_songs()
        for song in liked_songs:
            print(f"- {song}")

        # 2. Create a new playlist
        playlist_name = "My Awesome Playlist"
        playlist_desc = "A playlist created with code!"
        # new_playlist = spotify_client.create_playlist(playlist_name, description=playlist_desc)
        # print(f"\\nCreated playlist: {new_playlist['name']} (ID: {new_playlist['id']})")

        # 3. Search for a song and add it to the playlist
        # search_results = spotify_client.search_song("Never Gonna Give You Up", limit=1)
        # if search_results and search_results['tracks']['items']:
        #     song_to_add = search_results['tracks']['items'][0]['id']
        #     playlist_id = new_playlist['id']
        #     spotify_client.add_song_to_playlist(playlist_id, song_to_add)
        #     print(f"Added song to '{playlist_name}'")

        #     # 4. List songs in the new playlist
        #     print(f"\\nSongs in '{playlist_name}':")
        #     playlist_songs = spotify_client.list_songs(playlist_id)
        #     for song in playlist_songs:
        #         print(f"- {song}") 