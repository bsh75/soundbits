from dotenv import load_dotenv
import os
import time
from soundcloud import Client
from urllib.parse import urlparse
import json

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)


class SoundCloudClient(Client):
    def __init__(self):
        """
        Initializes the SoundCloudClient.
        It inherits from the soundcloud.Client and initializes it
        using credentials from a .env file and an access token from
        credentials.json.
        """
        self.client_id = os.getenv('CLIENT_ID')
        self.client_secret = os.getenv('CLIENT_SECRET')
        self.redirect_uri = os.getenv('REDIRECT_URI')
        self.creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')

        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("CLIENT_ID, CLIENT_SECRET, or REDIRECT_URI not set in .env file")

        access_token = self._get_access_token()
        super().__init__(client_id=self.client_id, client_secret=self.client_secret, access_token=access_token)

    def _get_access_token(self):
        """
        Retrieves the access token from credentials.json.
        If the file doesn't exist, it prompts the user to run the oauth script.
        """
        if not os.path.exists(self.creds_path):
            print("Credentials not found. Please run 'python soundbits/soundcloud/init_oauth.py' to authenticate.")
            return None
            
        with open(self.creds_path, 'r') as f:
            creds = json.load(f)
        
        # Here you could add logic to check if the token is expired and refresh it
        # using the 'refresh_token', but for now, we'll just use the access token.
        return creds.get('access_token')

    def get_user_tracks_by_permalink(self, permalink):
        """
        A new method to fetch all tracks for a user given their permalink.

        Args:
            permalink (str): The user's permalink or full profile URL.

        Returns:
            list: A list of track resources.
        """
        try:
            # If a full URL is passed, extract the permalink from the path
            if permalink.startswith('http'):
                parsed_url = urlparse(permalink)
                permalink = parsed_url.path.strip('/')

            # The soundcloud-python library expects a full URL for the 'url' param of /resolve
            resolve_url = f'https://soundcloud.com/{permalink}'
            user = self.get('/resolve', url=resolve_url)
            
            # Then, fetch the tracks for that user's ID
            tracks = self.get(f'/users/{user.id}/tracks')
            return tracks
        except Exception as e:
            print(f"Error fetching tracks for '{permalink}': {e}")
            return []