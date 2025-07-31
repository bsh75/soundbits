import os
from soundcloud import Client
from dotenv import load_dotenv
from urllib.parse import urlparse
import webbrowser
import json

def get_oauth_token():
    """
    Guides the user through the SoundCloud OAuth2 process to get an access token.
    This is required for making authenticated API requests.
    """
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(dotenv_path=dotenv_path)

    # Load your app's credentials from the .env file
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')
    redirect_uri = os.getenv('REDIRECT_URI')

    if not all([client_id, client_secret, redirect_uri]):
        print("Error: Make sure CLIENT_ID, CLIENT_SECRET, and REDIRECT_URI are set in your .env file.")
        return

    # Initialize the client with your app's credentials
    client = Client(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri
    )

    # 1. Get the authorization URL and open it in the browser
    auth_url = client.authorize_url()
    print("Opening the following URL in your browser for authorization:")
    print(auth_url)
    webbrowser.open(auth_url)

    # 2. Ask the user to paste the URL they are redirected to
    print("\nAfter authorizing, you will be redirected to a new URL.")
    print("Please copy that entire URL and paste it here:")
    redirected_url = input("> ").strip()

    # 3. Extract the authorization code from the redirected URL
    parsed_url = urlparse(redirected_url)
    try:
        code = [q.split("=")[1] for q in parsed_url.query.split("&") if q.startswith("code=")][0]
    except IndexError:
        print("\nError: Could not find 'code' in the redirected URL.")
        print("Please make sure you copied the correct URL.")
        return

    # 4. Exchange the authorization code for an access token
    try:
        token_response = client.exchange_token(code)
        access_token = token_response.access_token
        refresh_token = token_response.refresh_token
        
        # Save the tokens to a file for later use
        credentials = {
            'access_token': access_token,
            'refresh_token': refresh_token
        }
        creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
        with open(creds_path, 'w') as f:
            json.dump(credentials, f)
            
        print(f"\nSuccessfully authenticated! Tokens saved to {creds_path}")

    except Exception as e:
        print(f"\nAn error occurred while exchanging the token: {e}")

if __name__ == "__main__":
    get_oauth_token() 