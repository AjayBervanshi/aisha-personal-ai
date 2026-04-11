"""Quick script: Open Telegram Web, wait for QR code, save screenshot."""
import sys, io
#sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
from playwright.sync_api import sync_playwright

SESSION_DIR = Path("e:/VSCode/Aisha/tests/.telegram_session")
SHOT_DIR    = Path("e:/VSCode/Aisha/tests/screenshots")
SESSION_DIR.mkdir(parents=True, exist_ok=True)
SHOT_DIR.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(SESSION_DIR),
        headless=True,
        args=["--no-sandbox","--disable-dev-shm-usage","--disable-gpu"],
        viewport={"width": 1280, "height": 900},
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    print("Loading web.telegram.org ...")
    page.goto("https://web.telegram.org/k/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(8000)

    # Check if already logged in
    try:
        page.wait_for_selector('.chatlist-top, .sidebar-left', timeout=5000)
        print("LOGGED_IN")
        page.screenshot(path=str(SHOT_DIR / "logged_in.png"), full_page=True)
    except Exception:
        # Not logged in — wait for QR code canvas to appear
        print("NOT_LOGGED_IN - waiting for QR code...")
        try:
            page.wait_for_selector('canvas, .qr-container, img[src*="qr"]', timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(3000)
        page.screenshot(path=str(SHOT_DIR / "qr_code.png"), full_page=True)
        print("QR_CODE_SAVED: tests/screenshots/qr_code.png")

    ctx.close()
