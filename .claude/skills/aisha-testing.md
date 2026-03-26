---
name: aisha-testing
description: How to test Aisha — Telegram Web testing protocol, CDP connection, test scripts
type: project
---

# Aisha Testing Protocol

## CRITICAL: Always Use Telegram Web (Never Webhooks)

ALL testing MUST go through `web.telegram.org` in a real browser via Playwright CDP.
NEVER inject messages via `curl POST /webhook` — this bypasses auth and gives false positives.

## Setup: Connect to Edge via CDP

Edge must be running with: `--remote-debugging-port=9222`

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    context = browser.contexts[0]
    page = context.pages[0]
    # Navigate to Telegram Web
    page.goto("https://web.telegram.org")
```

## Run Smart Test Agent

```bash
PYTHONUTF8=1 /e/VSCode/.venv/Scripts/python tests/test_smart_agent.py
```

The smart agent randomizes test scenarios each run — different topics, questions, moods.

## Manual Test Commands to Send in Telegram

| Command | Tests |
|---------|-------|
| `/start` | Bot initialization |
| `/syscheck` | System health |
| `/aistatus` | AI provider availability |
| `/mood romantic` | Mood override |
| `/studio` | Content pipeline trigger |
| `/upgrade` | Self-improvement trigger |
| `Ek kahani sunao` | Hindi story generation |
| `What is love?` | English conversation |

## What to Verify After Each Test
1. Bot responds within 5 seconds
2. Hindi responses are in Devanagari (never Roman)
3. No error messages in the response
4. Check logs: `render logs` via MCP or Render dashboard
5. Check DB: `aisha_conversations` table for the saved message
