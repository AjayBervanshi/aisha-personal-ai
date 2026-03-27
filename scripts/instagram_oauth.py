# -*- coding: utf-8 -*-
"""
instagram_oauth.py
Opens Facebook OAuth in Edge, waits for you to log in,
then automatically captures the token from the redirect URL.
"""
import sys, json, time, requests
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent
ENV_PATH     = PROJECT_ROOT / ".env"
TOKEN_PATH   = PROJECT_ROOT / "tokens" / "instagram_token.json"

APP_ID     = "4335568243361662"   # Story With Aisha (Facebook App — updated 2026-03-26)
APP_SECRET = "502835b09707b7c47899d0e367bd5f3c"
IG_APP_ID  = "1486907126134254"  # Instagram App (Story With Aisha-IG)
IG_SECRET  = "62833d10182f2bdb42a136b74646392c"

OAUTH_URL = (
    f"https://www.facebook.com/dialog/oauth"
    f"?client_id={APP_ID}"
    f"&redirect_uri=https://www.facebook.com/connect/login_success.html"
    f"&scope=instagram_basic,instagram_content_publish,instagram_manage_media"
    f",pages_show_list,pages_read_engagement,business_management"
    f"&response_type=token"
)


def update_env(key, value):
    text  = ENV_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    done  = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            done = True
            break
    if not done:
        lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  .env updated: {key}=...{value[-20:]}")


def extend_to_long_lived(short_token):
    """Exchange short-lived token for 60-day token."""
    print("Extending to long-lived token...")
    r = requests.get(
        "https://graph.facebook.com/v19.0/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "fb_exchange_token": short_token,
        },
        timeout=15,
    )
    if r.status_code == 200:
        data  = r.json()
        token = data.get("access_token", short_token)
        days  = data.get("expires_in", 0) // 86400
        print(f"Long-lived token ready ({days} days)")
        return token
    print(f"Extension failed ({r.status_code}): {r.text[:150]}")
    return short_token


def get_page_token(user_token):
    """Get the Page Access Token for 'Story With Aisha' page."""
    r = requests.get(
        "https://graph.facebook.com/v19.0/me/accounts",
        params={"access_token": user_token},
        timeout=10,
    )
    pages = r.json().get("data", [])
    for page in pages:
        print(f"  Found page: {page['name']} (ID: {page['id']})")
        if "aisha" in page["name"].lower() or page["id"] == "1039347169258878":
            return page["access_token"], page["id"]
    if pages:
        return pages[0]["access_token"], pages[0]["id"]
    return user_token, None


def get_ig_business_id(page_token, page_id):
    """Get Instagram Business Account ID linked to the Facebook page."""
    r = requests.get(
        f"https://graph.facebook.com/v19.0/{page_id}",
        params={"fields": "instagram_business_account", "access_token": page_token},
        timeout=10,
    )
    ig = r.json().get("instagram_business_account", {})
    if ig:
        return ig.get("id")
    print("  No Instagram account linked to this page yet.")
    print("  -> Go to Instagram app -> Settings -> Linked Accounts -> Facebook -> link 'Story With Aisha' page")
    return None


def test_content_publish(token, ig_id):
    """Test if we can create a media container (dry run)."""
    test_img = "https://picsum.photos/1080/1080"
    r = requests.post(
        f"https://graph.facebook.com/v19.0/{ig_id}/media",
        params={"access_token": token},
        data={"image_url": test_img, "caption": "Test by Aisha", "published": "false"},
        timeout=15,
    )
    if r.status_code == 200:
        container_id = r.json().get("id")
        print(f"  Content publish: WORKS (container: {container_id})")
        return True
    print(f"  Content publish test: {r.status_code} {r.text[:200]}")
    return False


def run():
    from playwright.sync_api import sync_playwright

    print("Opening Facebook OAuth in Edge...")
    print("Log in with your Facebook account and allow permissions.")
    print("I will capture the token automatically after you log in.")

    captured = {"token": None}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="msedge",
            args=["--start-maximized"],
        )
        ctx  = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()

        # Monitor all URL changes for the redirect
        def on_url_change(new_url):
            if "login_success.html" in new_url and "access_token=" in new_url:
                # Extract token from URL fragment
                fragment = new_url.split("#")[-1] if "#" in new_url else ""
                params   = {}
                for part in fragment.split("&"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        params[k] = v
                token = params.get("access_token")
                if token:
                    captured["token"] = token
                    print(f"\nToken captured automatically: {token[:40]}...")

        page.on("framenavigated", lambda frame: on_url_change(frame.url) if frame == page.main_frame else None)

        page.goto(OAUTH_URL, wait_until="domcontentloaded")

        # Wait up to 3 minutes for user to log in and approve
        for _ in range(180):
            time.sleep(1)
            if captured["token"]:
                break
            # Also check current URL directly
            try:
                current = page.url
                if "login_success.html" in current and "access_token=" in current:
                    fragment = current.split("#")[-1] if "#" in current else ""
                    for part in fragment.split("&"):
                        if part.startswith("access_token="):
                            captured["token"] = part.split("=", 1)[1]
                            print(f"\nToken from URL: {captured['token'][:40]}...")
                            break
            except Exception:
                pass

        browser.close()

    token = captured["token"]
    if not token:
        print("No token captured. Did you complete the login?")
        return False

    print("\nProcessing token...")

    # Extend to long-lived
    long_token = extend_to_long_lived(token)

    # Get page token
    print("Getting page access token...")
    page_token, page_id = get_page_token(long_token)

    # Get Instagram Business ID
    ig_biz_id = None
    if page_id:
        print(f"Checking Instagram linked to page {page_id}...")
        ig_biz_id = get_ig_business_id(page_token, page_id)

    if not ig_biz_id:
        ig_biz_id = "26152640604399291"  # fallback to known ID
        print(f"Using known Instagram ID: {ig_biz_id}")

    # Test content publishing
    print("Testing content publish permission...")
    can_post = test_content_publish(page_token, ig_biz_id)

    # Save everything
    print("\nSaving to .env...")
    update_env("INSTAGRAM_ACCESS_TOKEN", page_token)
    update_env("INSTAGRAM_BUSINESS_ID", ig_biz_id)
    update_env("INSTAGRAM_APP_ID", APP_ID)
    update_env("META_PAGE_ID", page_id or "1039347169258878")

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    import datetime
    with open(TOKEN_PATH, "w") as f:
        json.dump({
            "user_token": long_token,
            "page_token": page_token,
            "page_id": page_id,
            "ig_business_id": ig_biz_id,
            "can_post": can_post,
            "created_at": datetime.datetime.now().isoformat(),
        }, f, indent=2)

    print(f"\nDone! Saved to {TOKEN_PATH}")
    print(f"Instagram Business ID: {ig_biz_id}")
    print(f"Can post content: {can_post}")
    return True


if __name__ == "__main__":
    run()
