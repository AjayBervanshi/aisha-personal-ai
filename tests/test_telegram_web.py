"""
test_telegram_web.py
====================
Tests Aisha on web.telegram.org via headless Playwright.
Uses a persistent session — scan QR code once, sessions persist.
"""

import os
import sys
import time
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


def run():
    with sync_playwright() as p:
        print("Launching headless Chromium with persistent session...")
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1280,900",
            ],
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(30000)

        print("Navigating to web.telegram.org/k/ ...")
        page.goto("https://web.telegram.org/k/", wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        shot(page, "01_load")

        # Check login state
        html = page.content()
        is_logged_in = (
            "chatlist" in html.lower()
            or "sidebar" in html.lower()
            or page.locator('.chatlist-top').count() > 0
        )

        if not is_logged_in:
            print("\n⚠️  Not logged in. Waiting for QR code to render...")
            page.wait_for_timeout(5000)
            shot(page, "02_qr_code")
            print("  Open tests/screenshots/02_qr_code.png")
            print("  Scan the QR code with your Telegram mobile app.")
            print("  Then re-run this script — session will be saved.")
            ctx.close()
            return

        print("✅ Logged in! Searching for Aisha bot...")
        shot(page, "02_logged_in")

        # Search for the bot
        try:
            search = page.locator('input.input-search-input').first
            search.wait_for(state="visible", timeout=10000)
            search.click()
            search.fill(BOT_USERNAME)
            page.wait_for_timeout(2500)
            shot(page, "03_search_results")

            # Click first result
            first = page.locator('.chatlist-chat').first
            first.wait_for(state="visible", timeout=5000)
            first.click()
            page.wait_for_timeout(2000)
            shot(page, "04_chat_opened")
            print(f"  ✅ Opened chat with {BOT_USERNAME}")
        except Exception as e:
            print(f"  ❌ Could not open bot chat: {e}")
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
