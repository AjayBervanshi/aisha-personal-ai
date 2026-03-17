# -*- coding: utf-8 -*-
"""
instagram_auth.py
Opens Meta Graph Explorer + runs a local server to capture the token.
User clicks a "Submit Token" button on localhost:8787 after generating.
"""
import os, json, sys, time, threading, requests
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent
TOKEN_PATH   = PROJECT_ROOT / "tokens" / "instagram_token.json"
ENV_PATH     = PROJECT_ROOT / ".env"

APP_ID     = "1486907126134254"
APP_SECRET = "62833d10182f2bdb42a136b74646392c"

# Shared state
captured_token = {"value": None}

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Aisha - Instagram Token Setup</title>
<style>
  body { font-family: Arial, sans-serif; max-width: 700px; margin: 60px auto; padding: 20px; background: #f5f5f5; }
  h1 { color: #833AB4; }
  .steps { background: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
  .step { margin: 12px 0; padding: 10px; border-left: 3px solid #833AB4; }
  textarea { width: 100%; height: 80px; padding: 10px; font-size: 13px; border: 2px solid #833AB4; border-radius: 6px; margin: 10px 0; }
  button { background: #833AB4; color: white; border: none; padding: 14px 30px; font-size: 16px; border-radius: 6px; cursor: pointer; width: 100%; }
  button:hover { background: #6a2d99; }
  .success { background: #d4edda; color: #155724; padding: 15px; border-radius: 6px; margin: 15px 0; }
  a { color: #833AB4; }
</style>
</head>
<body>
<h1>Aisha - Instagram Setup</h1>
<div class="steps">
  <b>Steps:</b>
  <div class="step">1. Open <a href="https://developers.facebook.com/tools/explorer/?app_id=1486907126134254&permissions=instagram_basic,instagram_content_publish,instagram_manage_media,pages_show_list,business_management" target="_blank">Meta Graph API Explorer</a> (opens in new tab)</div>
  <div class="step">2. Top dropdown: select <b>Story With Aisha-IG</b></div>
  <div class="step">3. Click <b>Generate Access Token</b></div>
  <div class="step">4. Check these permissions:<br>
    &nbsp;&nbsp;- instagram_basic<br>
    &nbsp;&nbsp;- instagram_content_publish<br>
    &nbsp;&nbsp;- instagram_manage_media<br>
    &nbsp;&nbsp;- pages_show_list<br>
    &nbsp;&nbsp;- business_management
  </div>
  <div class="step">5. Click <b>Generate Access Token</b> -> Login -> Allow</div>
  <div class="step">6. Copy the token and paste below</div>
</div>
<form method="POST" action="/submit">
  <textarea name="token" placeholder="Paste your token here (starts with IGAAV... or EAA...)"></textarea>
  <button type="submit">Submit Token to Aisha</button>
</form>
</body>
</html>"""

SUCCESS_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Success</title>
<style>body{font-family:Arial;text-align:center;margin:100px auto;max-width:500px;}
h1{color:#28a745;}.box{background:#d4edda;padding:30px;border-radius:10px;}</style>
</head><body>
<div class="box">
<h1>Token Captured!</h1>
<p>Aisha is now connected to Instagram.</p>
<p>You can close this tab.</p>
</div>
</body></html>"""


class TokenHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress server logs

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode("utf-8"))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length).decode("utf-8")
        params = parse_qs(body)
        token  = params.get("token", [""])[0].strip()

        if token:
            captured_token["value"] = token
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(SUCCESS_HTML.encode("utf-8"))
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No token provided.")

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()


def extend_token(short_token):
    print("Extending to long-lived token (60 days)...")
    r = requests.get(
        "https://graph.instagram.com/access_token",
        params={
            "grant_type": "ig_exchange_token",
            "client_secret": APP_SECRET,
            "access_token": short_token,
        },
        timeout=15,
    )
    if r.status_code == 200:
        data = r.json()
        long_token = data.get("access_token")
        expires    = data.get("expires_in", 5183944)
        print(f"Long-lived token ready. Expires in {expires // 86400} days.")
        return long_token
    print(f"Extension failed ({r.status_code}): {r.text[:200]}")
    return short_token


def get_instagram_user(token):
    r = requests.get(
        "https://graph.instagram.com/me",
        params={"fields": "id,username,account_type", "access_token": token},
        timeout=10,
    )
    return r.json() if r.status_code == 200 else {}


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


def save_token(token, biz_id):
    update_env("INSTAGRAM_ACCESS_TOKEN", token)
    update_env("INSTAGRAM_BUSINESS_ID", biz_id)
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    import datetime
    with open(TOKEN_PATH, "w") as f:
        json.dump({"access_token": token, "business_id": biz_id,
                   "created_at": datetime.datetime.now().isoformat()}, f, indent=2)
    print(f"Saved to .env + {TOKEN_PATH}")


def run():
    from playwright.sync_api import sync_playwright

    PORT = 8787
    server = HTTPServer(("localhost", PORT), TokenHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"Local server started on http://localhost:{PORT}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="msedge",
            args=["--start-maximized"],
        )
        ctx  = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        page.goto(f"http://localhost:{PORT}", wait_until="domcontentloaded")
        print("Browser opened. Follow the steps on the page.")

        # Wait until token is submitted (up to 5 minutes)
        for _ in range(300):
            time.sleep(1)
            if captured_token["value"]:
                break

        browser.close()
    server.shutdown()

    token = captured_token["value"]
    if not token:
        print("No token received. Exiting.")
        return False

    print(f"Token received: {token[:40]}...")
    long_token  = extend_token(token)
    final_token = long_token or token

    user     = get_instagram_user(final_token)
    biz_id   = user.get("id", "26152640604399291")
    username = user.get("username", "unknown")
    print(f"Instagram account: @{username} (ID: {biz_id})")

    save_token(final_token, biz_id)
    print(f"Done! Aisha connected to @{username} on Instagram.")
    return True


if __name__ == "__main__":
    run()
