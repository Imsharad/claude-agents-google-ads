import argparse
from google_auth_oauthlib.flow import InstalledAppFlow

def main():
    parser = argparse.ArgumentParser(description='Get a Refresh Token')
    parser.add_argument('--client_id', required=True, help='Client ID')
    parser.add_argument('--client_secret', required=True, help='Client Secret')
    args = parser.parse_args()

    # The scope for the Google Ads API
    scopes = ['https://www.googleapis.com/auth/adwords']

    # Create the flow
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": args.client_id,
                "client_secret": args.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=scopes
    )

    # Run the console flow
    print("Launching browser for authentication...")
    credential = flow.run_local_server(port=0)

    print("\n--- YOUR REFRESH TOKEN ---")
    print(credential.refresh_token)
    print("--------------------------\n")

if __name__ == '__main__':
    main()
