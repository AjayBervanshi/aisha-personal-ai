"""
test_telegram_edge.py
=====================
Tests Aisha on web.telegram.org using the real Edge browser profile.
Edge is already logged into Telegram — no QR code scan needed.

Run: PYTHONUTF8=1 /e/VSCode/.venv/Scripts/python tests/test_telegram_edge.py
"""
import sys, io, time
#sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

EDGE_PATH    = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
EDGE_PROFILE = "C:/Users/Admin/AppData/Local/Microsoft/Edge/User Data"
SHOT_DIR     = Path("e:/VSCode/Aisha/tests/screenshots")
BOT_USERNAME = "AishaPersonalBot"

SHOT_DIR.mkdir(parents=True, exist_ok=True)


def snap(page, name):
    p = SHOT_DIR / f"{name}.png"
    page.screenshot(path=str(p), full_page=True)
    print(f"  Screenshot: tests/screenshots/{p.name}")
    return p


def send_and_wait(page, text, wait_ms=25000):
    """Send message and return the last bot reply text."""
    # Count existing messages
    before = page.locator('div.message').count()

    composer = page.locator('div[contenteditable="true"]').last
    composer.click()
    page.wait_for_timeout(400)
    composer.type(text)
    page.keyboard.press("Enter")
    print(f"  Sent: {repr(text)}")

    # Wait for new message
    deadline = time.time() + wait_ms / 1000
    while time.time() < deadline:
        count = page.locator('div.message').count()
        if count > before:
            page.wait_for_timeout(2500)
            msgs = page.locator('div.message').all()
            if msgs:
                return msgs[-1].inner_text().strip()
        page.wait_for_timeout(600)
    return ""


def _check_edge_not_running():
    """Exit with clear message if Edge is already running (profile will be locked)."""
    import subprocess
    result = subprocess.run(
        ["tasklist"],
        capture_output=True, text=True
    )
    if "msedge.exe" in result.stdout.lower():
        print("\nEdge is currently running and its profile is locked.")
        print("Please close Microsoft Edge completely, then re-run this script.")
        print("\n  Close Edge: right-click taskbar icon -> Close all windows")
        print("  Or kill it: taskkill /IM msedge.exe /F")
        raise SystemExit(1)


def run():
    _check_edge_not_running()
    with sync_playwright() as p:
        print("Launching Edge with real profile (already logged in to Telegram)...")
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=EDGE_PROFILE,
            executable_path=EDGE_PATH,
            headless=True,
            channel="msedge",
            args=["--no-sandbox", "--disable-dev-shm-usage", "--profile-directory=Default"],
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(30000)

        print("Navigating to web.telegram.org ...")
        page.goto("https://web.telegram.org/k/", wait_until="domcontentloaded")
        page.wait_for_timeout(6000)
        snap(page, "01_telegram_load")

        # Detect login state
        content = page.content().lower()
        logged_in = any(k in content for k in ["chatlist", "sidebar-left", "im_dialogs"])

        if not logged_in:
            page.wait_for_timeout(5000)
            snap(page, "02_login_page")
            print("\nNot logged in on Edge profile.")
            print("Open tests/screenshots/02_login_page.png and scan the QR code.")
            ctx.close()
            return

        print("Logged in! Searching for AishaPersonalBot...")
        snap(page, "02_logged_in")

        # Search for bot
        try:
            search = page.locator('input.input-search-input, input[placeholder*="Search"]').first
            search.wait_for(state="visible", timeout=8000)
            search.click()
            search.fill(BOT_USERNAME)
            page.wait_for_timeout(2500)
            snap(page, "03_search")

            # Click first result
            page.locator('.chatlist-chat').first.click()
            page.wait_for_timeout(2000)
            snap(page, "04_chat")
            print(f"  Chat opened.")
        except Exception as e:
            snap(page, "03_error")
            print(f"Could not open bot chat: {e}")
            ctx.close()
            return

        # ── Tests ─────────────────────────────────────────────────────────
        tests = [
            ("Greeting",
             "Hi Aisha",
             ["hi", "hello", "hey", "ajay", "namaste"],
             []),
            ("Knows GitHub repo",
             "What is your GitHub repo?",
             ["ajaybervanshi", "aisha-personal-ai", "github.com"],
             ["no public repo", "agent-lightning"]),
            ("Knows Render hosting",
             "Where are you hosted?",
             ["render", "render.com"],
             ["agent-lightning", "distributed cloud"]),
            ("/syscheck clean output",
             "/syscheck",
             ["health", "gemini", "elevenlabs"],
             ["Error code: 401 - {'error'"]),
            ("Time is correct IST",
             "What time is it right now?",
             ["pm", "am", "ist"],
             ["4:06", "04:06"]),  # Old wrong time was ~4:06 PM
        ]

        passed, failed = 0, 0
        for i, (name, msg, expect, banned) in enumerate(tests, 1):
            print(f"\nTest {i}/{len(tests)}: {name}")
            reply = send_and_wait(page, msg)
            snap(page, f"test_{i:02d}_{name.replace(' ', '_')}")

            ok  = any(e.lower() in reply.lower() for e in expect) if expect else True
            bad = any(b.lower() in reply.lower() for b in banned)

            if ok and not bad:
                status = "PASS"
                passed += 1
            else:
                status = "FAIL"
                failed += 1

            icon = "OK" if status == "PASS" else "XX"
            print(f"  [{icon}] {status}")
            print(f"  Reply: {reply[:160]}")
            if not ok:
                print(f"  Expected any of: {expect}")
            if bad:
                found = [b for b in banned if b.lower() in reply.lower()]
                print(f"  Banned found: {found}")
            time.sleep(2)

        print(f"\n{'='*55}")
        print(f"RESULT: {passed}/{len(tests)} passed")
        print(f"Screenshots in: tests/screenshots/")
        ctx.close()


if __name__ == "__main__":
    run()
