"""
setup_youtube_oauth.py
======================
One-time setup wizard to authenticate Aisha with your YouTube account.
After running this script ONCE, Aisha can upload videos automatically forever.

HOW IT WORKS:
  1. You go to Google Cloud Console and create a free project (5 minutes, guided below)
  2. You download a client_secret.json file
  3. This script opens your browser → you log in → done
  4. Token is saved to tokens/youtube_token.json
  5. Aisha auto-refreshes it forever — you never need to do this again

COST: 100% FREE
  - YouTube Data API v3 has a free quota of 10,000 units/day
  - Uploading 1 video costs ~1600 units → you can upload ~6 videos/day for free
  - More than enough for our channels

Run this script:
  python scripts/setup_youtube_oauth.py
"""

import os
import sys
import json
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
TOKEN_PATH = PROJECT_ROOT / "tokens" / "youtube_token.json"
CLIENT_SECRET_PATH = PROJECT_ROOT / "tokens" / "youtube_client_secret.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def print_setup_guide():
    print("""
╔══════════════════════════════════════════════════════════════╗
║          AISHA — YouTube OAuth Setup (FREE)                  ║
╚══════════════════════════════════════════════════════════════╝

STEP 1: Create a Google Cloud Project (free)
─────────────────────────────────────────────
1. Open this URL in your browser:
   https://console.cloud.google.com/

2. Click "Create Project" → Name it "Aisha-YouTube" → Click Create

3. In the left menu → "APIs & Services" → "Enable APIs and Services"

4. Search "YouTube Data API v3" → Click it → Click "ENABLE"

5. Also search "YouTube Analytics API" → Enable it too


STEP 2: Create OAuth Credentials
──────────────────────────────────
1. Go to "APIs & Services" → "Credentials"

2. Click "+ CREATE CREDENTIALS" → "OAuth client ID"

3. If asked to configure consent screen:
   - Click "CONFIGURE CONSENT SCREEN"
   - Select "External" → Fill in:
     * App name: Aisha
     * User support email: your email
     * Developer contact: your email
   - Click "SAVE AND CONTINUE" through all steps
   - On "Test users" page, add YOUR Gmail address

4. Back in Credentials → "+ CREATE CREDENTIALS" → "OAuth client ID"
   - Application type: Desktop app
   - Name: Aisha Desktop
   - Click CREATE

5. Click "DOWNLOAD JSON" → Save it as:
   """ + str(CLIENT_SECRET_PATH) + """

6. Make sure the file is in the tokens/ folder


STEP 3: Run this script again after placing the file
──────────────────────────────────────────────────────
python scripts/setup_youtube_oauth.py

""")


def run_oauth_flow():
    """Run the YouTube OAuth flow and save the token."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        import google.auth
    except ImportError:
        print("Installing required packages...")
        os.system(f"{sys.executable} -m pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials

    # Check if token already exists and is valid
    creds = None
    if TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
            if creds and creds.valid:
                print("✅ YouTube token already exists and is valid!")
                print(f"   Token: {TOKEN_PATH}")
                return True
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                with open(TOKEN_PATH, "w") as f:
                    f.write(creds.to_json())
                print("✅ YouTube token refreshed successfully!")
                return True
        except Exception as e:
            print(f"Existing token invalid, re-authenticating: {e}")

    # Need fresh auth
    if not CLIENT_SECRET_PATH.exists():
        print(f"\n❌ client_secret.json not found at:\n   {CLIENT_SECRET_PATH}")
        print("\nPlease follow the setup guide above first.")
        print_setup_guide()
        return False

    print("\n🌐 Opening browser for YouTube authentication...")
    print("   Log in with the YouTube account you want Aisha to use.")
    print("   After logging in, the browser will show a success page.\n")

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRET_PATH), SCOPES
        )
        creds = flow.run_local_server(
            port=8080,
            success_message="Aisha is now connected to YouTube! You can close this tab.",
            open_browser=True,
        )

        # Save token
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        token_data = json.loads(creds.to_json())
        token_data["client_id"] = os.getenv("YOUTUBE_CLIENT_ID", "")
        token_data["client_secret"] = os.getenv("YOUTUBE_CLIENT_SECRET", "")

        with open(TOKEN_PATH, "w") as f:
            json.dump(token_data, f, indent=2)

        print(f"\n✅ SUCCESS! YouTube token saved to:\n   {TOKEN_PATH}")
        print("\n📺 Aisha can now:")
        print("   - Upload videos to YouTube automatically")
        print("   - Pull YouTube Analytics data")
        print("   - Manage video metadata (titles, descriptions, thumbnails)")
        print("\n🔑 Add to your .env file:")
        print(f"   YOUTUBE_CLIENT_ID=<from your client_secret.json>")
        print(f"   YOUTUBE_CLIENT_SECRET=<from your client_secret.json>")
        return True

    except Exception as e:
        print(f"\n❌ OAuth flow failed: {e}")
        print("Make sure port 8080 is free and try again.")
        return False


def test_youtube_connection():
    """Quick test to verify YouTube API is working."""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        if not TOKEN_PATH.exists():
            print("❌ No token found. Run setup first.")
            return False

        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        youtube = build("youtube", "v3", credentials=creds)

        # Get channel info
        request = youtube.channels().list(part="snippet,statistics", mine=True)
        response = request.execute()

        if response.get("items"):
            channel = response["items"][0]
            name = channel["snippet"]["title"]
            subs = channel["statistics"].get("subscriberCount", "?")
            print(f"\n✅ Connected to YouTube channel: {name}")
            print(f"   Subscribers: {subs}")
            return True
        else:
            print("❌ No YouTube channel found for this account")
            return False

    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


if __name__ == "__main__":
    print("\n🎬 Aisha YouTube Setup Wizard\n")

    if "--test" in sys.argv:
        test_youtube_connection()
        sys.exit(0)

    if "--guide" in sys.argv:
        print_setup_guide()
        sys.exit(0)

    # Check if client secret exists
    if not CLIENT_SECRET_PATH.exists():
        print_setup_guide()
        input("\nPress ENTER after placing client_secret.json in the tokens/ folder...")

    success = run_oauth_flow()

    if success:
        print("\n🧪 Testing connection...")
        test_youtube_connection()
        print("\n🚀 You're all set! Aisha will now auto-upload videos.")
        print("   To test: python scripts/setup_youtube_oauth.py --test")
    else:
        print("\n💜 Need help? Check the guide above or contact Ajay.")
