"""
Playwright script to capture Instagram FB token from Graph Explorer.
Runs in foreground, polls for EAA token, saves to file then exits.
"""
import sys
from playwright.sync_api import sync_playwright
import time, json

# Fix Windows cp1252 console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from pathlib import Path

TOKEN_OUT = Path(__file__).parent.parent / "tokens" / "instagram_fb_token.txt"
TOKEN_OUT.parent.mkdir(exist_ok=True)

POLL_JS = """
() => {
    // Check all inputs and textareas for EAA tokens
    const els = document.querySelectorAll('input, textarea, [contenteditable]');
    for (const el of els) {
        const v = el.value || el.innerText || '';
        if (v.startsWith('EAA') && v.length > 50) return v;
    }
    // Also check clipboard-style divs
    const divs = document.querySelectorAll('div');
    for (const d of divs) {
        const t = d.innerText || '';
        if (t.startsWith('EAA') && t.length > 50 && t.length < 500) return t.trim();
    }
    return null;
}
"""

print("Opening Meta Graph Explorer...")

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
    )
    ctx = browser.new_context(
        viewport={"width": 1400, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    page = ctx.new_page()

    page.goto("https://developers.facebook.com/tools/explorer/", timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    print("Page loaded:", page.title())
    print("\nWaiting for you to generate a token with EAA prefix...")
    print("(I will auto-capture when token appears on screen)\n")

    found_token = None
    for i in range(120):  # wait up to 10 minutes
        time.sleep(5)
        try:
            token = page.evaluate(POLL_JS)
            if token:
                found_token = token
                print(f"\nGOT TOKEN: {token[:50]}...")
                break
        except Exception as e:
            pass

        if i % 6 == 0:
            print(f"  Still watching... ({(i*5)//60}m {(i*5)%60}s elapsed)")

    if found_token:
        TOKEN_OUT.write_text(found_token)
        print(f"Saved to {TOKEN_OUT}")
        # Show success overlay
        try:
            page.evaluate("""
                () => {
                    const div = document.createElement('div');
                    div.style = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);background:#00c853;color:white;padding:16px 32px;border-radius:8px;font-size:18px;font-weight:bold;z-index:99999;box-shadow:0 4px 12px rgba(0,0,0,0.3)';
                    div.innerText = 'Token captured! You can close this browser.';
                    document.body.appendChild(div);
                }
            """)
        except:
            pass
        time.sleep(4)
    else:
        print("Timed out waiting for token.")

    browser.close()

print("Browser closed.")
if found_token:
    print(f"\nToken saved to: {TOKEN_OUT}")
    print("Run the main setup now.")
