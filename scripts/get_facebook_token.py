# -*- coding: utf-8 -*-
"""
Opens Facebook OAuth in Edge, waits for login_success redirect,
captures token from URL automatically. No sleep loop.
"""
import sys, json, requests
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
TOKEN_PATH = PROJECT_ROOT / "tokens" / "instagram_token.json"

APP_ID = "1486907126134254"
APP_SECRET = "62833d10182f2bdb42a136b74646392c"

OAUTH_URL = (
    f"https://www.facebook.com/dialog/oauth"
    f"?client_id={APP_ID}"
    f"&redirect_uri=https://www.facebook.com/connect/login_success.html"
    f"&scope=instagram_basic,instagram_content_publish,instagram_manage_media"
    f",pages_show_list,pages_read_engagement,business_management"
    f"&response_type=token"
)

def update_env(key, value):
    text = ENV_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return
    lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

def process_token(token):
    print(f"Token received: {token[:50]}...")

    # Try to extend with new app
    print("Extending token...")
    r = requests.get("https://graph.facebook.com/v19.0/oauth/access_token", params={
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": token,
    }, timeout=15)
    if r.status_code == 200:
        long_token = r.json()["access_token"]
        days = r.json().get("expires_in", 0) // 86400
        print(f"Extended: {days} days")
    else:
        print(f"Extension failed ({r.status_code}): {r.text[:100]}")
        long_token = token

    # Get Facebook pages
    r2 = requests.get("https://graph.facebook.com/v19.0/me/accounts",
                      params={"access_token": long_token}, timeout=10)
    pages = r2.json().get("data", [])
    print(f"Pages found: {len(pages)}")
    for p in pages:
        print(f"  - {p['name']} (ID: {p['id']})")

    page_token = long_token
    page_id = None
    ig_id = "26152640604399291"

    if pages:
        page = next((p for p in pages if "aisha" in p["name"].lower()), pages[0])
        page_token = page["access_token"]
        page_id = page["id"]

        # Check Instagram linked
        r3 = requests.get(f"https://graph.facebook.com/v19.0/{page_id}",
                          params={"fields": "instagram_business_account", "access_token": page_token}, timeout=10)
        ig = r3.json().get("instagram_business_account", {})
        if ig:
            ig_id = ig.get("id", ig_id)
            print(f"Instagram Business ID: {ig_id}")
        else:
            print("No Instagram linked to page yet.")
            print("-> Instagram app -> Settings -> Linked Accounts -> Facebook -> link page")

    # Test posting
    print("Testing content publish...")
    r4 = requests.post(f"https://graph.facebook.com/v19.0/{ig_id}/media",
                       params={"access_token": page_token},
                       data={"image_url": "https://picsum.photos/1080/1080",
                             "caption": "Test", "published": "false"}, timeout=15)
    can_post = r4.status_code == 200
    print(f"Can post: {can_post} ({r4.status_code}) {r4.text[:150]}")

    # Save
    update_env("INSTAGRAM_ACCESS_TOKEN", page_token)
    update_env("INSTAGRAM_BUSINESS_ID", ig_id)
    if page_id:
        update_env("META_PAGE_ID", page_id)

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    import datetime
    with open(TOKEN_PATH, "w") as f:
        json.dump({"user_token": long_token, "page_token": page_token,
                   "page_id": page_id, "ig_business_id": ig_id,
                   "can_post": can_post,
                   "created_at": datetime.datetime.now().isoformat()}, f, indent=2)
    print(f"Saved to {TOKEN_PATH}")
    return can_post

def run():
    from playwright.sync_api import sync_playwright

    print("Opening Facebook login in Edge...")
    print("Log in and approve permissions. Token will be captured automatically.")

    token = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="msedge",
                                    args=["--start-maximized"])
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(OAUTH_URL, wait_until="domcontentloaded")

        # Wait for the redirect to login_success.html (up to 3 minutes)
        try:
            page.wait_for_url("https://www.facebook.com/connect/login_success.html*", timeout=180000)
            url = page.url
            print(f"Redirected to: {url[:80]}...")
            # Extract token from URL fragment via JS
            token = page.evaluate("""
                () => {
                    const hash = window.location.hash || window.location.href.split('#')[1] || '';
                    const params = {};
                    hash.split('&').forEach(p => {
                        const [k, v] = p.split('=');
                        if (k && v) params[k] = decodeURIComponent(v);
                    });
                    return params['access_token'] || null;
                }
            """)
            if not token:
                # fallback: parse URL manually
                fragment = url.split("#")[-1] if "#" in url else ""
                for part in fragment.split("&"):
                    if part.startswith("access_token="):
                        token = part.split("=", 1)[1]
                        break
        except Exception as e:
            print(f"Wait failed: {e}")

        browser.close()

    if token:
        print(f"Token captured: {token[:40]}...")
        process_token(token)
    else:
        print("No token captured. You can paste the token manually:")
        print("Format: EAA...")

if __name__ == "__main__":
    run()
