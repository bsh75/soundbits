import os
from spotify_client import SpotifyAPI
from dotenv import load_dotenv
from collections import defaultdict

def get_all_user_tracks(client):
    """
    Fetches all unique tracks from a user's liked songs, playlists, and saved albums.
    """
    print("Fetching all your songs... (This might take a moment)")
    
    unique_track_ids = set()
    all_tracks = []

    def add_tracks(items):
        for item in items:
            track = item.get('track')
            if track and track['id'] and track['id'] not in unique_track_ids:
                unique_track_ids.add(track['id'])
                all_tracks.append(track)

    # 1. Liked Songs
    add_tracks(client.list_songs())
    print(f"Found {len(all_tracks)} tracks in liked songs.")

    # 2. Playlists
    playlists = client.sp_user.current_user_playlists()
    for playlist in playlists['items']:
        print(f"Fetching songs from playlist: {playlist['name']}")
        add_tracks(client.list_songs(playlist_id=playlist['id']))
    
    print(f"Found {len(all_tracks)} unique tracks after scanning playlists.")

    # 3. Saved Albums
    albums = client.sp_user.current_user_saved_albums()
    while albums:
        for item in albums['items']:
            album = item.get('album')
            if album and album.get('tracks'):
                album_tracks = album['tracks']['items']
                # The album object from saved_albums doesn't contain full track info,
                # so we need to fetch them. To optimize, we fetch all at once.
                track_ids = [t['id'] for t in album_tracks if t]
                if track_ids:
                    full_track_details = client.sp_public.tracks(track_ids)['tracks']
                    for track in full_track_details:
                         if track and track['id'] and track['id'] not in unique_track_ids:
                            unique_track_ids.add(track['id'])
                            all_tracks.append(track)
        
        if albums['next']:
            albums = client.sp_user.next(albums)
        else:
            albums = None

    print(f"Found {len(all_tracks)} unique tracks in total.")
    return all_tracks

def main():
    load_dotenv()
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    REDIRECT_URI = os.getenv("REDIRECT_URI")

    if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
        print("Missing Spotify credentials in .env file.")
        return

    client = SpotifyAPI(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
    
    all_tracks = get_all_user_tracks(client)
    
    # Get all genres from the user's library by batch fetching artist details
    print("Analyzing your library's genres...")
    artist_genres_cache = {}
    artist_ids = {track['artists'][0]['id'] for track in all_tracks if track and track.get('artists')}
    
    artist_id_list = list(artist_ids)
    for i in range(0, len(artist_id_list), 50):
        chunk = artist_id_list[i:i+50]
        artists_details = client.sp_public.artists(chunk)['artists']
        for artist in artists_details:
            if artist:
                artist_genres_cache[artist['id']] = artist.get('genres', [])
    
    user_genres = set()
    for genres in artist_genres_cache.values():
        user_genres.update(genres)
    
    sorted_genres = sorted(list(user_genres))
    
    # Let the user choose a genre with a search-and-confirm workflow
    chosen_genres = []
    while not chosen_genres:
        search_term = input("\nEnter a genre to search for (e.g., 'rock', 'house'): ").lower()
        if not search_term:
            continue

        matched_genres = [g for g in sorted_genres if search_term in g.lower()]

        if not matched_genres:
            print(f"No genres found matching '{search_term}'. Please try again.")
            continue

        print("\nFound the following matching genres:")
        for i, genre in enumerate(matched_genres):
            print(f"- {genre}")
        
        confirm = input("Create a playlist with these genres? (y/n): ").lower()
        if confirm == 'y':
            chosen_genres = matched_genres
    
    # Filter songs by the chosen group of genres
    genre_tracks = []
    for track in all_tracks:
        if track and track.get('artists'):
            artist_id = track['artists'][0]['id']
            artist_genres = artist_genres_cache.get(artist_id, [])
            if any(genre in chosen_genres for genre in artist_genres):
                genre_tracks.append(track)

    if not genre_tracks:
        print(f"No tracks found for the selected genres.")
        return

    # Sort tracks by artist, then by popularity
    genre_tracks.sort(key=lambda t: (t['artists'][0]['name'], -t.get('popularity', 0)))
    
    # Use the original search term for the playlist name
    playlist_name = f"{search_term.replace(' ', '_').capitalize()}_sb"
    new_playlist = client.create_playlist(playlist_name, description=f"A curated playlist of {search_term} genres.")
    print(f"\nCreated playlist: '{playlist_name}'")
    
    # Add tracks in chunks of 100
    track_uris = [t['uri'] for t in genre_tracks]
    client.add_song_to_playlist(new_playlist['id'], track_uris)
    
    print(f"Added {len(genre_tracks)} songs to the playlist.")

if __name__ == '__main__':
    main() 