"""
test_telegram_web.py
====================
Tests Aisha on web.telegram.org via headless Playwright.
Uses a persistent session — scan QR code once, sessions persist.
"""

import os
import sys
import io
import time
#sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

SESSION_DIR  = Path("e:/VSCode/Aisha/tests/.telegram_session")
SHOT_DIR     = Path("e:/VSCode/Aisha/tests/screenshots")
BOT_USERNAME = "AishaPersonalBot"   # without @

SESSION_DIR.mkdir(parents=True, exist_ok=True)
SHOT_DIR.mkdir(parents=True, exist_ok=True)


def shot(page, name):
    p = SHOT_DIR / f"{name}.png"
    page.screenshot(path=str(p), full_page=True)
    print(f"  📸 {p.name}")
    return p


def send_and_wait(page, text, wait_ms=20000):
    """Send a message and wait for bot reply, return reply text."""
    # Get count of messages before sending
    before = page.locator('div.message').count()

    # Type into the message composer
    composer = page.locator('div[contenteditable="true"]').last
    composer.click()
    page.wait_for_timeout(300)
    composer.fill(text)
    page.keyboard.press("Enter")
    print(f"  → Sent: {text!r}")

    # Wait for new message to appear
    start = time.time()
    while (time.time() - start) * 1000 < wait_ms:
        count = page.locator('div.message').count()
        if count > before:
            page.wait_for_timeout(2000)  # let full reply render
            msgs = page.locator('div.message').all()
            if msgs:
                return msgs[-1].inner_text()
        page.wait_for_timeout(500)
    return ""


def _is_logged_in(page) -> bool:
    """Check actual visible DOM elements — avoid false positives from JS/CSS in login page."""
    return (
        page.locator('.chatlist-chat').count() > 0
        or page.locator('#column-left').count() > 0
        or page.locator('.chat-input').count() > 0
    )


def run():
    with sync_playwright() as p:
        # ── First pass: check login state headlessly ──────────────────────────
        print("Checking Telegram session...")
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://web.telegram.org/k/", wait_until="domcontentloaded")
        page.wait_for_timeout(6000)
        logged_in = _is_logged_in(page)
        ctx.close()

        # ── If not logged in: relaunch headed so user can scan QR ────────────
        if not logged_in:
            print("\nNot logged in. Opening a visible browser window for QR scan...")
            print("Scan the QR code in the browser window that opens, then wait.")
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=str(SESSION_DIR),
                headless=False,
                args=["--no-sandbox"],
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto("https://web.telegram.org/k/", wait_until="domcontentloaded")
            print("Waiting up to 120s for you to scan the QR code...")
            deadline = time.time() + 120
            while time.time() < deadline:
                if _is_logged_in(page):
                    print("QR scan detected! Session saved. Re-running tests headlessly...")
                    page.wait_for_timeout(3000)
                    ctx.close()
                    break
                time.sleep(2)
            else:
                print("Timed out waiting for QR scan. Please re-run the script.")
                ctx.close()
                return

            # Reopen headless now that session is saved
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=str(SESSION_DIR),
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto("https://web.telegram.org/k/", wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
        else:
            # ── Already logged in: open fresh headless context for tests ─────
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=str(SESSION_DIR),
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.set_default_timeout(30000)
            page.goto("https://web.telegram.org/k/", wait_until="domcontentloaded")
            page.wait_for_timeout(6000)

        page.set_default_timeout(30000)
        shot(page, "01_load")
        print("Logged in! Searching for Aisha bot...")
        shot(page, "02_logged_in")

        # Search for the bot — try multiple known Telegram Web K selectors
        try:
            # Try clicking the search/pencil icon to open search
            for search_sel in [
                'input[placeholder*="Search"]',
                'input[placeholder*="search"]',
                '.input-search input',
                '.search-super-content input',
                'input.input-field-input',
                'input',
            ]:
                search = page.locator(search_sel).first
                if search.count() > 0:
                    try:
                        search.wait_for(state="visible", timeout=3000)
                        break
                    except Exception:
                        continue
            else:
                # Fallback: press Ctrl+F or click the search button
                page.keyboard.press("Control+k")
                page.wait_for_timeout(1000)
                search = page.locator('input').first

            search.click()
            search.fill(BOT_USERNAME)
            page.wait_for_timeout(3000)
            shot(page, "03_search_results")

            # Click first result
            first = page.locator('.chatlist-chat').first
            first.wait_for(state="visible", timeout=8000)
            first.click()
            page.wait_for_timeout(2000)
            shot(page, "04_chat_opened")
            print(f"  Opened chat with {BOT_USERNAME}")
        except Exception as e:
            print(f"  Could not open bot chat: {e}")
            shot(page, "03_search_failed")
            ctx.close()
            return

        # ── Tests ─────────────────────────────────────────────────────────
        tests = [
            ("Basic greeting",         "Hi Aisha",
             ["hi", "hello", "hey", "ajay", "namaste"], []),
            ("Know her GitHub repo",    "What is your GitHub repo?",
             ["ajaybervanshi", "aisha-personal-ai", "github.com"], ["no public repo", "agent-lightning"]),
            ("Know she's on Render",    "Where are you hosted?",
             ["render", "render.com"], ["agent-lightning", "distributed cloud"]),
            ("/syscheck command",       "/syscheck",
             ["health", "gemini", "elevenlabs"], ["Error code: 401 - {'error'"]),
        ]

        passed, failed = 0, 0
        for i, (name, msg, expect_any, banned) in enumerate(tests, 1):
            print(f"\nTest {i}/{len(tests)}: {name}")
            reply = send_and_wait(page, msg)
            shot(page, f"test_{i:02d}_{name.replace(' ', '_')}")

            ok  = any(e.lower() in reply.lower() for e in expect_any) if expect_any else True
            bad = any(b.lower() in reply.lower() for b in banned)

            if ok and not bad:
                status = "✅ PASS"
                passed += 1
            else:
                status = "❌ FAIL"
                failed += 1

            print(f"  {status}")
            print(f"  Reply: {reply[:150]}")
            if not ok:
                print(f"  Expected any of: {expect_any}")
            if bad:
                print(f"  Banned phrase found: {[b for b in banned if b.lower() in reply.lower()]}")

        print(f"\n{'='*50}")
        print(f"RESULT: {passed}/{len(tests)} passed — {'🎉 ALL GOOD' if failed==0 else '⚠️ SOME FAILURES'}")
        print(f"Screenshots: tests/screenshots/")
        ctx.close()


if __name__ == "__main__":
    run()
