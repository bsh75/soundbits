import os
import time
from spotify_client import SpotifyAPI
from dotenv import load_dotenv
from collections import Counter

def analyze_playlist_genres(client, playlist_tracks, top_n=3):
    """
    Analyzes the genre distribution of a list of tracks and returns the top 3.
    """
    genre_counter = Counter()
    artist_ids = set()
    for item in playlist_tracks:
        track = item.get('track')
        if track and track.get('artists'):
            artist_ids.add(track['artists'][0]['id'])

    # Batch fetch artist details to get genres
    artist_genres = {}
    artist_id_list = list(artist_ids)
    for i in range(0, len(artist_id_list), 50):
        chunk = artist_id_list[i:i+50]
        artists_details = client.sp_public.artists(chunk)['artists']
        for artist in artists_details:
            if artist:
                artist_genres[artist['id']] = artist.get('genres', [])

    # Count genres
    for item in playlist_tracks:
        track = item.get('track')
        if track and track.get('artists'):
            primary_artist_id = track['artists'][0]['id']
            genre_counter.update(artist_genres.get(primary_artist_id, []))

    return [genre for genre, count in genre_counter.most_common(top_n)]

def main():
    load_dotenv()
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    REDIRECT_URI = os.getenv("REDIRECT_URI")

    if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
        print("Missing Spotify credentials in .env file.")
        return

    client = SpotifyAPI(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)

    # 1. Get all liked songs and pre-fetch artist genres for efficiency
    print("Fetching liked songs and artist genres...")
    liked_songs = client.list_songs()
    liked_song_ids = {item['track']['id'] for item in liked_songs if item.get('track')}
    
    artist_ids_from_liked = {
        item['track']['artists'][0]['id'] 
        for item in liked_songs 
        if item.get('track') and item['track'].get('artists')
    }
    
    artist_genres_cache = {}
    artist_id_list = list(artist_ids_from_liked)
    for i in range(0, len(artist_id_list), 50):
        chunk = artist_id_list[i:i+50]
        artists_details = client.sp_public.artists(chunk)['artists']
        for artist in artists_details:
            if artist:
                artist_genres_cache[artist['id']] = artist.get('genres', [])
    print(f"Found {len(liked_song_ids)} liked songs and cached genres for {len(artist_genres_cache)} artists.")

    # 2. Get user's playlists
    playlists = client.sp_user.current_user_playlists()['items']

    for playlist in playlists:
        original_name = playlist['name']
        
        # Skip playlists that are already enhanced or owned by others
        if original_name.endswith('_sb') or playlist['owner']['id'] != client.user_id:
            continue

        print(f"\nProcessing playlist: '{original_name}'")
        
        # 3. Create a new playlist
        new_playlist_name = f"{original_name}_sb"
        new_playlist = client.create_playlist(new_playlist_name, description=f"Enhanced version of {original_name}")
        
        # 4. Copy original songs
        original_tracks = client.list_songs(playlist_id=playlist['id'])
        original_track_uris = [item['track']['uri'] for item in original_tracks if item.get('track')]
        
        if original_track_uris:
            client.add_song_to_playlist(new_playlist['id'], original_track_uris)
            print(f"Copied {len(original_track_uris)} songs to '{new_playlist_name}'.")

        # 5. Analyze genres
        top_genres = analyze_playlist_genres(client, original_tracks, top_n=3)
        print(f"Top genres for this playlist: {top_genres}")

        # 6. Find matching liked songs to add
        songs_to_add_uris = []
        original_song_ids = {item['track']['id'] for item in original_tracks if item.get('track')}
        
        for item in liked_songs:
            track = item.get('track')
            if not track or track['id'] in original_song_ids:
                continue

            # Use the cache for a fast, local genre lookup
            primary_artist_id = track['artists'][0]['id'] if track.get('artists') else None
            if primary_artist_id and any(genre in top_genres for genre in artist_genres_cache.get(primary_artist_id, [])):
                songs_to_add_uris.append(track['uri'])

        # 7. Add new songs
        if songs_to_add_uris:
            client.add_song_to_playlist(new_playlist['id'], songs_to_add_uris)
            print(f"Added {len(songs_to_add_uris)} new songs from your liked tracks.")
        else:
            print("No new songs from liked tracks to add.")
        
        time.sleep(1) # Add a delay between processing each playlist

if __name__ == '__main__':
    main() 