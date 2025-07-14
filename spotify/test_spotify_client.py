import unittest
import os
from spotify_client import SpotifyAPI
from dotenv import load_dotenv

class TestSpotifyAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Set up the SpotifyAPI client for all tests.
        """
        load_dotenv()
        CLIENT_ID = os.getenv("CLIENT_ID")
        CLIENT_SECRET = os.getenv("CLIENT_SECRET")
        REDIRECT_URI = os.getenv("REDIRECT_URI")

        if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
            raise unittest.SkipTest("Spotify credentials not found in .env file.")

        cls.spotify_client = SpotifyAPI(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
        cls.test_song_name = "Bohemian Rhapsody - Remastered 2011"
        cls.test_playlist_name = "Test Playlist_sb"
        cls.song_id = None
        cls.playlist_id = None

    def test_01_search_song(self):
        """
        Test that we can search for a song and get a valid result.
        """
        print("\nTesting song search...")
        results = self.spotify_client.search_song(self.test_song_name, limit=1)
        self.assertIsNotNone(results)
        track = results['tracks']['items'][0]
        TestSpotifyAPI.song_id = track['id']
        self.assertIsNotNone(self.song_id)
        print(f"Found song '{track['name']}' with ID: {self.song_id}")

    def test_02_get_song_data(self):
        """
        Test fetching metadata and genre for a song.
        """
        self.assertIsNotNone(self.song_id, "Song ID not found; cannot run data tests.")
        print(f"\nTesting data retrieval for song ID: {self.song_id}...")
        
        metadata = self.spotify_client.get_song_metadata(self.song_id)
        self.assertIsNotNone(metadata)
        print("Successfully fetched song metadata.")

        genres = self.spotify_client.get_song_genre(self.song_id)
        self.assertIsNotNone(genres)
        self.assertIsInstance(genres, list)
        print(f"Successfully fetched genres: {genres}")

    def test_03_list_liked_songs(self):
        """
        Test listing the user's liked songs.
        """
        print("\nTesting listing liked songs...")
        liked_songs_items = self.spotify_client.list_songs()
        self.assertIsNotNone(liked_songs_items)
        if liked_songs_items:
            self.assertIn('added_at', liked_songs_items[0])
            self.assertIn('track', liked_songs_items[0])
        print(f"Found {len(liked_songs_items)} liked songs.")

    def test_04_playlist_lifecycle(self):
        """
        Test the full lifecycle of a playlist: create, add, remove, and delete.
        """
        self.assertIsNotNone(self.song_id, "Song ID not found; cannot run playlist tests.")
        print(f"\nTesting playlist lifecycle with song ID: {self.song_id}...")
        
        # Test creating a playlist (the client should add the suffix)
        playlist = self.spotify_client.create_playlist("Test Playlist")
        self.assertIsNotNone(playlist)
        self.assertTrue(playlist['name'].endswith('_sb'))
        TestSpotifyAPI.playlist_id = playlist['id']
        print(f"Created playlist '{playlist['name']}' with ID: {self.playlist_id}")

        # Test guard against modifying a non-_sb playlist (by trying to add to a newly created one without the suffix)
        unprotected_playlist = self.spotify_client.sp_user.user_playlist_create(self.spotify_client.user_id, "unprotected_playlist", public=True, description="temp")
        add_result = self.spotify_client.add_song_to_playlist(unprotected_playlist['id'], [self.song_id])
        self.assertIsNone(add_result)
        print("Correctly blocked adding song to unprotected playlist.")
        self.spotify_client.sp_user.current_user_unfollow_playlist(unprotected_playlist['id'])
        
        # Continue with the protected playlist
        self.spotify_client.add_song_to_playlist(self.playlist_id, [self.song_id])
        print("Added song to playlist.")

        song_items = self.spotify_client.list_songs(playlist_id=self.playlist_id)
        song_ids_in_playlist = [item['track']['id'] for item in song_items if item and item.get('track')]
        self.assertIn(self.song_id, song_ids_in_playlist)
        print("Verified song was added to playlist.")

        self.spotify_client.remove_song_from_playlist(self.playlist_id, [self.song_id])
        print("Removed song from playlist.")
        
        song_items_after_removal = self.spotify_client.list_songs(playlist_id=self.playlist_id)
        song_ids_after_removal = [item['track']['id'] for item in song_items_after_removal if item and item.get('track')]
        self.assertNotIn(self.song_id, song_ids_after_removal)
        print("Verified song was removed from playlist.")

        self.spotify_client.delete_playlist(self.playlist_id)
        print("Deleted the test playlist.")

if __name__ == '__main__':
    unittest.main() 