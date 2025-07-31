from soundcloud_client import SoundCloudClient

def test_user_tracks():
    """
    Initializes the SoundCloud client and fetches tracks for a user.
    """
    try:
        # Initialize your custom client
        client = SoundCloudClient()
        # If the client initialized without a token, it will have printed a message.
        if not client.access_token:
            return  # Exit if no access token
    except ValueError as e:
        print(f"Error initializing client: {e}")
        return

    # The permalink of the user you want to fetch tracks from
    # This is the part of their profile URL, e.g., soundcloud.com/USERNAME
    user_permalink = 'https://soundcloud.com/brett-hockey'  # Example: deadmau5

    print(f"Attempting to fetch tracks for user: '{user_permalink}'...")
    
    # Use the new method to get the user's tracks
    tracks = client.get_user_tracks_by_permalink(user_permalink)

    if tracks:
        print(f"\nSuccessfully fetched {len(tracks)} tracks for '{user_permalink}':")
        for i, track in enumerate(tracks):
            print(f"{i + 1}. {track.title} (ID: {track.id})")
    else:
        print(f"\nCould not fetch tracks for '{user_permalink}'.")
        print("Please ensure your credentials.json file is present and valid.")

if __name__ == "__main__":
    test_user_tracks() 