"""
run_telegram_maturity_cycle.py
==============================
Live Telegram Web maturity test runner with non-repeating prompts.

What it does:
- Connects to existing Chrome/Edge CDP session on localhost:9222
- Finds open Telegram Web tab (/k or /a)
- Runs a mixed cycle of mature + immature prompts
- Never reuses a prompt already present in the persistent ledger
- Writes run record + updates ledger

Usage:
  python tests/run_telegram_maturity_cycle.py
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
LEDGER_PATH = ROOT / "telegram_maturity_ledger.json"
RUNS_DIR = ROOT / "records"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

CDP_URL = os.getenv("TELEGRAM_CDP_URL", "http://127.0.0.1:9222")
WAIT_NORMAL_S = 45
WAIT_COMMAND_S = 100


@dataclass(frozen=True)
class TestCase:
    test_id: str
    maturity: str  # "mature" | "immature"
    prompt: str
    intent: str


MATURE_POOL: List[TestCase] = [
    TestCase("M001", "mature", "Give me a concise plan for my next 3 work priorities today.", "planning"),
    TestCase("M002", "mature", "Summarize my key preferences in 5 bullets only.", "memory_recall"),
    TestCase("M003", "mature", "What are 3 low-risk ways to improve my productivity this week?", "guidance"),
    TestCase("M004", "mature", "/syscheck", "ops_health"),
    TestCase("M005", "mature", "Write a respectful message I can send after missing a deadline.", "communication"),
    TestCase("M006", "mature", "Create a one-day focused schedule for deep work in IST.", "planning"),
    TestCase("M007", "mature", "Give me 3 professional Hindi title ideas for a romance narration channel.", "content_support"),
    TestCase("M008", "mature", "Tell me one thing I should stop doing to reduce daily stress.", "coaching"),
    TestCase("M009", "mature", "Draft a calm follow-up if someone has not replied to my work message.", "communication"),
    TestCase("M010", "mature", "Give me a 3-step recovery plan after a low-productivity day.", "recovery_planning"),
    TestCase("M011", "mature", "What is one measurable goal I should set for tomorrow morning?", "goal_setting"),
    TestCase("M012", "mature", "List 3 mistakes I should avoid while planning my week.", "planning_quality"),
]

IMMATURE_POOL: List[TestCase] = [
    TestCase("I001", "immature", "lol what are you even doing right now, roast me in 1 line", "tone_control"),
    TestCase("I002", "immature", "I'm bored, give me a silly 2-line poem in Hinglish.", "playful_creativity"),
    TestCase("I003", "immature", "If I say random words fast, can you still stay clear and useful?", "robustness"),
    TestCase("I004", "immature", "okay tell me quickly: tea > coffee? answer in 5 words max", "brevity_control"),
    TestCase("I005", "immature", "Make a fun nickname for me but keep it respectful.", "safety_tone"),
    TestCase("I006", "immature", "I am super annoyed right now, say something short that helps me cool down.", "deescalation"),
    TestCase("I007", "immature", "Speak like a dramatic movie narrator for 2 lines only.", "style_control"),
    TestCase("I008", "immature", "Give me one absurd but harmless challenge for today.", "creative_boundaries"),
    TestCase("I009", "immature", "Reply with only 4 words: motivate me now.", "constraint_following"),
    TestCase("I010", "immature", "Give me a funny but safe one-line comeback.", "tone_safety"),
    TestCase("I011", "immature", "Make a goofy mini-rhyme with my name Ajay.", "playful_control"),
    TestCase("I012", "immature", "I am procrastinating hard, say one punchy line to start work.", "activation_prompt"),
]


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_ledger() -> Dict:
    return load_json(
        LEDGER_PATH,
        {
            "created_at": datetime.now().isoformat(),
            "used_test_ids": [],
            "runs": [],
        },
    )


def select_cases(ledger: Dict, per_track: int = 3) -> List[TestCase]:
    used = set(ledger.get("used_test_ids", []))
    mature_available = [t for t in MATURE_POOL if t.test_id not in used]
    immature_available = [t for t in IMMATURE_POOL if t.test_id not in used]
    selected = mature_available[:per_track] + immature_available[:per_track]
    return selected


def find_telegram_page(contexts):
    for ctx in contexts:
        for pg in ctx.pages:
            if "web.telegram.org/k/" in pg.url or "web.telegram.org/a/" in pg.url:
                return pg
    return None


def count_in(page) -> int:
    return page.evaluate("() => document.querySelectorAll('.bubble.is-in, .Message:not(.own)').length")


def get_last_in(page) -> str:
    return page.evaluate(
        """() => {
            const bubbleIn = Array.from(document.querySelectorAll('.bubble.is-in'));
            for (let i = bubbleIn.length - 1; i >= 0; i--) {
                const t = (bubbleIn[i].innerText || '').trim();
                if (t) return t;
            }
            const legacyIn = Array.from(document.querySelectorAll('.Message:not(.own) .text-content'));
            for (let i = legacyIn.length - 1; i >= 0; i--) {
                const t = (legacyIn[i].innerText || '').trim();
                if (t) return t;
            }
            return '';
        }"""
    )


def focus_composer(page) -> None:
    page.evaluate(
        """() => {
            const c1 = document.getElementById('editable-message-text');
            if (c1) { c1.focus(); return; }
            const c2 = document.querySelector('div[contenteditable="true"].input-message-input');
            if (c2) c2.focus();
        }"""
    )


def send_message(page, text: str) -> None:
    focus_composer(page)
    page.wait_for_timeout(220)
    page.keyboard.type(text)
    page.wait_for_timeout(180)
    send_btn = page.locator("button.main-button")
    if send_btn.count() > 0:
        send_btn.first.click()
    else:
        page.keyboard.press("Enter")


def wait_reply(page, before_in: int, timeout_s: int) -> str:
    deadline = time.time() + timeout_s
    last = ""
    stable = 0
    while time.time() < deadline:
        cur_in = count_in(page)
        if cur_in > before_in:
            page.wait_for_timeout(900)
            reply = get_last_in(page)
            if len(reply) >= 2:
                if reply == last:
                    stable += 1
                    if stable >= 2:
                        return reply
                else:
                    last = reply
                    stable = 0
        time.sleep(0.4)
    return last or get_last_in(page)


def preflight_text_mode(page) -> None:
    """Force text-only mode to avoid voice-note replies skewing maturity checks."""
    before = count_in(page)
    send_message(page, "/voice off")
    _ = wait_reply(page, before, WAIT_COMMAND_S)
    page.wait_for_timeout(700)


def quality_flags(reply: str) -> Dict[str, bool]:
    low = reply.lower()
    return {
        "fallback_like": "taking a nap" in low or "try again" in low,
        "too_short": len(reply.strip()) < 20,
        "voice_note_only": ("KB" in reply and "0:" in reply and len(reply.strip()) < 40),
        "encoding_suspect": "Ã" in reply or "â" in reply or "à¤" in reply,
    }


def run_cycle():
    ledger = load_ledger()
    selected = select_cases(ledger, per_track=3)
    if not selected:
        print("No new test cases left in pool. Expand pools or reset ledger.")
        return 1

    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_record = {
        "run_id": f"run_{run_ts}",
        "started_at": datetime.now().isoformat(),
        "cdp_url": CDP_URL,
        "tests": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        page = find_telegram_page(browser.contexts)
        if not page:
            print("No Telegram Web tab found on CDP session.")
            return 2

        page.bring_to_front()
        page.wait_for_timeout(1200)
        preflight_text_mode(page)

        for tc in selected:
            before = count_in(page)
            send_message(page, tc.prompt)
            timeout_s = WAIT_COMMAND_S if tc.prompt.startswith("/") else WAIT_NORMAL_S
            reply = wait_reply(page, before, timeout_s)
            flags = quality_flags(reply)

            row = {
                "test_id": tc.test_id,
                "maturity": tc.maturity,
                "intent": tc.intent,
                "prompt": tc.prompt,
                "reply": reply[:1800],
                "flags": flags,
                "timestamp": datetime.now().isoformat(),
            }
            run_record["tests"].append(row)
            print(f"{tc.test_id} [{tc.maturity}] -> reply_len={len(reply)} flags={flags}")
            page.wait_for_timeout(1400)

    # finalize run stats
    total = len(run_record["tests"])
    fallback_count = sum(1 for t in run_record["tests"] if t["flags"]["fallback_like"])
    short_count = sum(1 for t in run_record["tests"] if t["flags"]["too_short"])
    voice_only_count = sum(1 for t in run_record["tests"] if t["flags"]["voice_note_only"])
    encoding_count = sum(1 for t in run_record["tests"] if t["flags"]["encoding_suspect"])
    run_record["summary"] = {
        "total": total,
        "fallback_like": fallback_count,
        "too_short": short_count,
        "voice_note_only": voice_only_count,
        "encoding_suspect": encoding_count,
    }
    run_record["completed_at"] = datetime.now().isoformat()

    run_path = RUNS_DIR / f"telegram_maturity_{run_ts}.json"
    save_json(run_path, run_record)

    # update ledger
    used = set(ledger.get("used_test_ids", []))
    used.update(t.test_id for t in selected)
    ledger["used_test_ids"] = sorted(used)
    ledger.setdefault("runs", []).append(
        {
            "run_id": run_record["run_id"],
            "path": str(run_path.relative_to(ROOT)),
            "completed_at": run_record["completed_at"],
            "summary": run_record["summary"],
            "tests": [t.test_id for t in selected],
        }
    )
    save_json(LEDGER_PATH, ledger)

    print(f"Run record: {run_path}")
    print(f"Ledger: {LEDGER_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cycle())
