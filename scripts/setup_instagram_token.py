"""
setup_instagram_token.py
========================
Step-by-step guide + token tester for Instagram Business API.
After following these steps, Aisha can post Reels and images automatically.

COST: 100% FREE
  - Meta Graph API is free
  - Instagram must be a Business or Creator account (free to convert)

Run:
  python scripts/setup_instagram_token.py
  python scripts/setup_instagram_token.py --test
"""

import os
import sys
import json
import requests
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent
TOKEN_PATH = PROJECT_ROOT / "tokens" / "instagram_token.json"


def print_setup_guide():
    print("""
╔══════════════════════════════════════════════════════════════╗
║         AISHA — Instagram API Setup (FREE)                   ║
╚══════════════════════════════════════════════════════════════╝

REQUIREMENTS:
  ✅ Instagram account (must be Business or Creator type)
  ✅ Facebook account (needed to link to Instagram)
  ✅ Free Meta Developer account

STEP 1: Convert Instagram to Business Account (if not already)
───────────────────────────────────────────────────────────────
1. Open Instagram app → Profile → Settings (3 lines)
2. Account → Switch to Professional Account → Creator or Business
3. Follow the steps (it's free, takes 2 minutes)

STEP 2: Link Instagram to a Facebook Page
───────────────────────────────────────────
1. Go to https://www.facebook.com
2. Create a Page (or use existing one)
3. In Instagram Settings → Linked Accounts → Facebook → link your page

STEP 3: Create Meta Developer App
───────────────────────────────────
1. Go to https://developers.facebook.com/
2. Click "My Apps" → "Create App"
3. Select "Other" → "Business" type
4. Fill in App name: "Aisha" → Create App

STEP 4: Add Instagram Graph API
──────────────────────────────────
1. In your app dashboard, click "Add Products"
2. Find "Instagram Graph API" → click "Set Up"
3. Under "Instagram Basic Display", add your Instagram account for testing

STEP 5: Get Your Access Token
──────────────────────────────
1. Go to https://developers.facebook.com/tools/explorer/
2. Select your App from dropdown
3. Click "Generate Access Token"
4. In permissions, add:
   - instagram_basic
   - instagram_content_publish
   - pages_show_list
   - business_management
5. Click "Generate Access Token" → log in → allow permissions
6. Copy the token

STEP 6: Get Long-Lived Token (60-day token, free)
───────────────────────────────────────────────────
Run: python scripts/setup_instagram_token.py --extend <YOUR_SHORT_TOKEN>

This converts the short token to a 60-day token.
For a permanent token (never expires), you need to use a System User token
via Meta Business Suite (takes ~10 more minutes — run --help for guide).

STEP 7: Add to .env file
──────────────────────────
INSTAGRAM_ACCESS_TOKEN=<your_long_lived_token>
INSTAGRAM_BUSINESS_ID=<your_instagram_business_account_id>

To find your Business Account ID:
  python scripts/setup_instagram_token.py --find-id <your_token>

""")


def extend_token(short_token: str) -> str | None:
    """Convert short-lived token to long-lived (60 days)."""
    app_id = os.getenv("INSTAGRAM_APP_ID") or os.getenv("META_APP_ID")
    app_secret = os.getenv("INSTAGRAM_APP_SECRET") or os.getenv("META_APP_SECRET")

    if not app_id or not app_secret:
        print("\n⚠️  Need INSTAGRAM_APP_ID and INSTAGRAM_APP_SECRET in .env")
        print("   Find these in your Meta Developer App → Basic Settings")
        return None

    try:
        response = requests.get(
            "https://graph.facebook.com/v19.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": short_token,
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            long_token = data.get("access_token")
            expires_in = data.get("expires_in", 5183944)

            # Save token
            TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(TOKEN_PATH, "w") as f:
                json.dump({
                    "access_token": long_token,
                    "expires_in_seconds": expires_in,
                    "created_at": __import__("datetime").datetime.now().isoformat()
                }, f, indent=2)

            print(f"\n✅ Long-lived token created!")
            print(f"   Expires in: {expires_in // 86400} days")
            print(f"   Saved to: {TOKEN_PATH}")
            print(f"\n   Add to .env:\n   INSTAGRAM_ACCESS_TOKEN={long_token}")
            return long_token
        else:
            print(f"❌ Token extension failed: {response.status_code} {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def find_business_id(token: str):
    """Find the Instagram Business Account ID for a given token."""
    try:
        # Get Facebook pages
        pages_response = requests.get(
            "https://graph.facebook.com/v19.0/me/accounts",
            params={"access_token": token},
            timeout=10
        )

        if pages_response.status_code != 200:
            print(f"❌ Failed to get pages: {pages_response.text}")
            return

        pages = pages_response.json().get("data", [])
        print(f"\n📄 Found {len(pages)} Facebook Page(s):")

        for page in pages:
            page_id = page["id"]
            page_token = page["access_token"]
            print(f"\n   Page: {page['name']} (ID: {page_id})")

            # Get linked Instagram account
            ig_response = requests.get(
                f"https://graph.facebook.com/v19.0/{page_id}",
                params={
                    "fields": "instagram_business_account",
                    "access_token": page_token,
                },
                timeout=10
            )

            if ig_response.status_code == 200:
                ig_data = ig_response.json().get("instagram_business_account", {})
                if ig_data:
                    ig_id = ig_data.get("id")
                    print(f"   Instagram Business ID: {ig_id}")
                    print(f"\n   Add to .env:\n   INSTAGRAM_BUSINESS_ID={ig_id}")
                else:
                    print("   ⚠️  No Instagram Business account linked to this page")

    except Exception as e:
        print(f"❌ Error finding business ID: {e}")


def test_instagram_connection():
    """Test if the Instagram API connection works."""
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    business_id = os.getenv("INSTAGRAM_BUSINESS_ID")

    if not token:
        # Try loading from token file
        if TOKEN_PATH.exists():
            with open(TOKEN_PATH) as f:
                token = json.load(f).get("access_token")

    if not token:
        print("❌ No Instagram token found.")
        print("   Set INSTAGRAM_ACCESS_TOKEN in .env or run setup first.")
        return False

    try:
        # Test token
        me_response = requests.get(
            "https://graph.facebook.com/v19.0/me",
            params={"access_token": token},
            timeout=10
        )

        if me_response.status_code != 200:
            print(f"❌ Token invalid: {me_response.text}")
            return False

        me = me_response.json()
        print(f"\n✅ Token valid!")
        print(f"   Account: {me.get('name', 'Unknown')} (ID: {me.get('id')})")

        if business_id:
            ig_response = requests.get(
                f"https://graph.facebook.com/v19.0/{business_id}",
                params={
                    "fields": "name,followers_count,media_count",
                    "access_token": token,
                },
                timeout=10
            )
            if ig_response.status_code == 200:
                ig = ig_response.json()
                print(f"   Instagram: {ig.get('name')} | Followers: {ig.get('followers_count', '?')} | Posts: {ig.get('media_count', '?')}")

        print("\n✅ Aisha is ready to post on Instagram!")
        return True

    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


def interactive_setup():
    """Interactive setup that asks for token and tests it."""
    print("\n📱 Aisha Instagram Setup Wizard\n")
    print("Have you already followed the setup guide? (yes/no)")
    ans = input("> ").strip().lower()

    if ans != "yes":
        print_setup_guide()
        print("\nFollow the guide above, then run this script again.")
        return

    token = input("\nPaste your Access Token here: ").strip()
    if not token:
        print("❌ No token provided")
        return

    print("\nPaste your Instagram Business Account ID (or leave blank to auto-find): ")
    biz_id = input("> ").strip()

    if not biz_id:
        print("\n🔍 Searching for your Instagram Business ID...")
        find_business_id(token)
        biz_id = input("\nEnter the Instagram Business ID from above: ").strip()

    # Save to .env hint
    print(f"\n📝 Add these to your .env file:")
    print(f"   INSTAGRAM_ACCESS_TOKEN={token}")
    print(f"   INSTAGRAM_BUSINESS_ID={biz_id}")

    # Save token file
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        json.dump({"access_token": token, "business_id": biz_id}, f, indent=2)

    print(f"\n✅ Token saved to {TOKEN_PATH}")
    print("\n🧪 Testing connection...")

    os.environ["INSTAGRAM_ACCESS_TOKEN"] = token
    os.environ["INSTAGRAM_BUSINESS_ID"] = biz_id
    test_instagram_connection()


if __name__ == "__main__":
    if "--guide" in sys.argv:
        print_setup_guide()
    elif "--test" in sys.argv:
        test_instagram_connection()
    elif "--extend" in sys.argv:
        idx = sys.argv.index("--extend")
        if idx + 1 < len(sys.argv):
            extend_token(sys.argv[idx + 1])
        else:
            print("Usage: python setup_instagram_token.py --extend <SHORT_TOKEN>")
    elif "--find-id" in sys.argv:
        idx = sys.argv.index("--find-id")
        if idx + 1 < len(sys.argv):
            find_business_id(sys.argv[idx + 1])
        else:
            print("Usage: python setup_instagram_token.py --find-id <TOKEN>")
    else:
        interactive_setup()
