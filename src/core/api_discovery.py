"""
api_discovery.py
================
Web Search Agent — finds API signup guides for any platform and notifies Ajay via Telegram.

Features:
  1. search_api_signup(platform)          — DuckDuckGo search → structured result
  2. notify_ajay_api_setup(platform)      — search + format + Telegram message to Ajay
  3. discover_free_alternatives(service)  — find free alternative APIs when one fails
  4. check_and_alert_dead_apis()          — daily audit hook: renewal links for dead keys

Search backend: DuckDuckGo (no API key needed) via `duckduckgo_search` package.
LLM extraction:  NVIDIA NIM LLaMA-3.3-70b via KEY_05 / KEY_06 pool.
Notifications:   Telegram bot (token loaded from Supabase api_keys table).
"""

import os
import re
import logging
import requests
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

log = logging.getLogger("Aisha.APIDiscovery")

# ── Constants ─────────────────────────────────────────────────────────────────

AJAY_TELEGRAM_ID = int(os.getenv("AJAY_TELEGRAM_ID", "1002381172"))
SUPABASE_URL     = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY     = (
    os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
)

# NVIDIA NIM — LLaMA-3.3 keys for extraction (KEY_05 and KEY_06 are chat pool A/B)
_NVIDIA_CHAT_KEYS = [
    os.getenv("NVIDIA_KEY_05", ""),
    os.getenv("NVIDIA_KEY_06", ""),
    os.getenv("NVIDIA_KEY_18", ""),  # Chat C — fallback
]
_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
_LLAMA_MODEL     = "meta/llama-3.3-70b-instruct"

# ── Telegram helpers ───────────────────────────────────────────────────────────

def _get_bot_token() -> str:
    """Load Telegram bot token from Supabase api_keys table, fallback to env."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if token:
        return token

    if not SUPABASE_URL or not SUPABASE_KEY:
        log.warning("[APIDiscovery] Supabase credentials missing — cannot load bot token")
        return ""

    try:
        headers = {
            "apikey":        SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/api_keys?name=eq.TELEGRAM_BOT_TOKEN&select=secret",
            headers=headers,
            timeout=10,
        )
        if r.status_code == 200 and r.json():
            return r.json()[0]["secret"]
    except Exception as e:
        log.warning(f"[APIDiscovery] Failed to fetch bot token from Supabase: {e}")

    return ""


def _send_telegram(message: str, parse_mode: str = "Markdown") -> bool:
    """Send a message to Ajay's Telegram chat. Returns True on success."""
    token = _get_bot_token()
    if not token:
        log.error("[APIDiscovery] No Telegram bot token — cannot send message")
        return False

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id":    AJAY_TELEGRAM_ID,
                "text":       message,
                "parse_mode": parse_mode,
            },
            timeout=15,
        )
        if r.status_code == 200:
            log.info("[APIDiscovery] Telegram message sent to Ajay")
            return True
        else:
            log.warning(f"[APIDiscovery] Telegram send failed {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        log.error(f"[APIDiscovery] Telegram send error: {e}")
        return False


# ── DuckDuckGo search ──────────────────────────────────────────────────────────

def _ddg_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search DuckDuckGo and return a list of result dicts.
    Each dict has: title, href, body.
    Falls back to empty list if duckduckgo_search is not installed.
    """
    try:
        from duckduckgo_search import DDGS  # type: ignore
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        log.info(f"[APIDiscovery] DDG search '{query[:50]}' → {len(results)} results")
        return results
    except ImportError:
        log.error(
            "[APIDiscovery] duckduckgo_search not installed. "
            "Run: pip install duckduckgo_search"
        )
        return []
    except Exception as e:
        log.warning(f"[APIDiscovery] DDG search failed: {e}")
        return []


# ── NVIDIA NIM LLM extraction ──────────────────────────────────────────────────

def _nvidia_extract(system_prompt: str, user_message: str) -> str:
    """
    Use NVIDIA NIM LLaMA-3.3 to extract structured info from search results.
    Tries KEY_05 → KEY_06 → KEY_18 in order.
    Returns empty string on failure.
    """
    for key in _NVIDIA_CHAT_KEYS:
        key = key.strip()
        if not key or not key.startswith("nvapi-"):
            continue
        try:
            r = requests.post(
                _NVIDIA_BASE_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Accept":        "application/json",
                },
                json={
                    "model":       _LLAMA_MODEL,
                    "messages":    [
                        {"role": "system",  "content": system_prompt},
                        {"role": "user",    "content": user_message},
                    ],
                    "max_tokens":  1024,
                    "temperature": 0.3,
                    "top_p":       0.9,
                },
                timeout=60,
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            elif r.status_code in (404, 402):
                log.warning(f"[APIDiscovery] NVIDIA {r.status_code} for key ending ...{key[-6:]}")
                continue
            else:
                log.warning(f"[APIDiscovery] NVIDIA {r.status_code}: {r.text[:100]}")
                continue
        except Exception as e:
            log.warning(f"[APIDiscovery] NVIDIA call error: {e}")
            continue

    log.error("[APIDiscovery] All NVIDIA LLaMA keys failed — returning raw text")
    return ""


# ── URL extraction helpers ─────────────────────────────────────────────────────

def _extract_best_url(results: list[dict], platform: str) -> str:
    """
    Try to find the most relevant signup/docs URL from DuckDuckGo results.
    Priority: official domain → console/dashboard → docs/api → first result.
    """
    platform_lower = platform.lower().replace(" ", "")

    # Keywords that strongly indicate a direct signup or key generation page
    priority_keywords = [
        "console", "dashboard", "keys", "api-key", "apikey",
        "signup", "sign-up", "register", "create-account",
    ]

    scored: list[tuple[int, str]] = []
    for res in results:
        url = res.get("href", "")
        if not url:
            continue
        url_lower = url.lower()
        score = 0
        # Prefer official platform domain
        if platform_lower in url_lower:
            score += 10
        for kw in priority_keywords:
            if kw in url_lower:
                score += 3
        if "docs" in url_lower or "documentation" in url_lower:
            score += 1
        scored.append((score, url))

    if not scored:
        return ""

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def _extract_urls_from_text(text: str) -> list[str]:
    """Extract all HTTP(S) URLs from a text block."""
    return re.findall(r"https?://[^\s\)\]\"'<>]+", text)


# ── Main class ─────────────────────────────────────────────────────────────────

class APIDiscoveryAgent:
    """
    Searches the web for API signup guides and notifies Ajay via Telegram.

    Usage:
        agent = APIDiscoveryAgent()
        result = agent.search_api_signup("groq")
        agent.notify_ajay_api_setup("groq")
        alternatives = agent.discover_free_alternatives("openai")
        agent.check_and_alert_dead_apis()
    """

    # ── search_api_signup ──────────────────────────────────────────────────────

    def search_api_signup(self, platform: str) -> dict:
        """
        Search DuckDuckGo for how to get an API key for `platform`.

        Returns:
            {
                "platform":   str,
                "signup_url": str,
                "steps":      list[str],   # 3-5 numbered steps
                "free_tier":  str,         # e.g. "Free: 60 req/min"
                "sources":    list[str],   # source URLs
            }
        """
        log.info(f"[APIDiscovery] Searching API signup guide for: {platform}")

        # DuckDuckGo search
        query = f"how to get free API key for {platform} site:official OR site:docs OR site:console"
        results = _ddg_search(query, max_results=6)

        if not results:
            # Simpler fallback query
            results = _ddg_search(f"{platform} API key get started free", max_results=5)

        if not results:
            return {
                "platform":   platform,
                "signup_url": "",
                "steps":      ["Search failed — DuckDuckGo returned no results."],
                "free_tier":  "Unknown",
                "sources":    [],
            }

        # Collect raw text and URLs
        sources = [r.get("href", "") for r in results if r.get("href")]
        raw_text = "\n\n".join(
            f"Title: {r.get('title', '')}\nURL: {r.get('href', '')}\nSummary: {r.get('body', '')}"
            for r in results
        )

        signup_url = _extract_best_url(results, platform)

        # Use NVIDIA LLaMA-3.3 to extract structured steps + free tier info
        system_prompt = (
            "You are an API documentation expert. "
            "Given search results about how to get an API key for a platform, "
            "extract concise, accurate information. "
            "Always prefer direct signup/console URLs. "
            "Output ONLY the requested JSON — no explanation."
        )
        user_message = f"""
Platform: {platform}

Search results:
{raw_text[:3000]}

Extract and return ONLY this JSON (no markdown fences, no extra text):
{{
  "signup_url": "<direct URL to get/create the API key>",
  "steps": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ...",
    "Step 4: ..."
  ],
  "free_tier": "<brief free tier description, e.g. 'Free: 6,000 tokens/min, 500k/day'>"
}}
"""
        llm_output = _nvidia_extract(system_prompt, user_message)

        # Parse LLM JSON response
        steps: list[str] = []
        free_tier = "Check official docs for free tier details"
        extracted_url = signup_url

        if llm_output:
            try:
                import json
                # Strip any accidental markdown fences
                clean = re.sub(r"```[a-z]*\n?", "", llm_output).strip()
                data = json.loads(clean)
                if data.get("signup_url"):
                    extracted_url = data["signup_url"]
                steps     = data.get("steps", [])
                free_tier = data.get("free_tier", free_tier)
            except Exception as parse_err:
                log.warning(f"[APIDiscovery] LLM JSON parse failed: {parse_err}")
                # Fallback: extract steps from text with regex
                step_matches = re.findall(r"(?:Step\s+\d+[:.]\s*|^\d+[.)]\s*)(.+)", llm_output, re.MULTILINE)
                steps = [s.strip() for s in step_matches[:5]] if step_matches else []

        # Last resort: build minimal steps if LLM failed
        if not steps:
            steps = [
                f"Go to the {platform} website",
                "Create an account or log in",
                "Navigate to API Keys / Developer settings",
                "Click 'Create API Key' and copy it",
            ]

        if not extracted_url and sources:
            extracted_url = sources[0]

        return {
            "platform":   platform,
            "signup_url": extracted_url,
            "steps":      steps,
            "free_tier":  free_tier,
            "sources":    sources[:3],
        }

    # ── notify_ajay_api_setup ──────────────────────────────────────────────────

    def notify_ajay_api_setup(self, platform: str) -> bool:
        """
        Search for platform API → format a friendly Telegram guide → send to Ajay.
        Returns True if message was sent successfully.
        """
        log.info(f"[APIDiscovery] Notifying Ajay about API setup for: {platform}")
        info = self.search_api_signup(platform)

        signup_url = info.get("signup_url", "")
        steps      = info.get("steps", [])
        free_tier  = info.get("free_tier", "")
        sources    = info.get("sources", [])

        # Format numbered steps with emoji digits
        emoji_digits = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
        step_lines = []
        for i, step in enumerate(steps[:5]):
            emoji = emoji_digits[i] if i < len(emoji_digits) else f"{i+1}."
            step_lines.append(f"{emoji} {step}")

        steps_text = "\n".join(step_lines) if step_lines else "Check official docs for steps."

        signup_line = f"\n🔗 *Direct link:* {signup_url}" if signup_url else ""
        free_line   = f"\n\n💚 *Free tier:* {free_tier}" if free_tier else ""
        source_line = f"\n📚 *Source:* {sources[0]}" if sources else ""

        message = (
            f"🔍 *API Setup Guide: {platform}*\n"
            f"\nTo get your free {platform} API key:\n\n"
            f"{steps_text}"
            f"{signup_line}"
            f"{free_line}"
            f"{source_line}\n\n"
            f"_Reply with the new key and I'll update it automatically!_ 💜"
        )

        return _send_telegram(message)

    # ── discover_free_alternatives ─────────────────────────────────────────────

    def discover_free_alternatives(self, failing_service: str) -> list[dict]:
        """
        When a service fails, find free alternatives.
        E.g., failing_service='groq' → returns list of alternatives with signup URLs.

        Returns:
            list of {
                "name": str,
                "description": str,
                "signup_url": str,
                "free_tier": str,
            }
        """
        log.info(f"[APIDiscovery] Finding alternatives for failing service: {failing_service}")

        query = f"free {failing_service} alternative LLM API 2024 2025 no credit card"
        results = _ddg_search(query, max_results=6)

        if not results:
            return []

        raw_text = "\n\n".join(
            f"Title: {r.get('title', '')}\nURL: {r.get('href', '')}\nSummary: {r.get('body', '')}"
            for r in results
        )

        system_prompt = (
            "You are an AI/API expert. Given search results about alternatives to a failing AI service, "
            "list the best free alternatives. Output ONLY JSON — no markdown, no extra text."
        )
        user_message = f"""
Failing service: {failing_service}

Search results:
{raw_text[:3000]}

Return ONLY this JSON array (up to 4 alternatives):
[
  {{
    "name": "Service Name",
    "description": "One sentence about what it is",
    "signup_url": "https://...",
    "free_tier": "Free: X req/min or X tokens/day"
  }}
]
"""
        llm_output = _nvidia_extract(system_prompt, user_message)

        if llm_output:
            try:
                import json
                clean = re.sub(r"```[a-z]*\n?", "", llm_output).strip()
                alternatives = json.loads(clean)
                if isinstance(alternatives, list):
                    log.info(f"[APIDiscovery] Found {len(alternatives)} alternatives for {failing_service}")
                    return alternatives
            except Exception as e:
                log.warning(f"[APIDiscovery] Alternative parse failed: {e}")

        # Fallback: build minimal list from search URLs
        fallbacks = []
        for r in results[:3]:
            url = r.get("href", "")
            title = r.get("title", "Unknown")
            fallbacks.append({
                "name":        title[:50],
                "description": r.get("body", "")[:100],
                "signup_url":  url,
                "free_tier":   "Check website for free tier",
            })
        return fallbacks

    # ── check_and_alert_dead_apis ──────────────────────────────────────────────

    def check_and_alert_dead_apis(self) -> None:
        """
        Called from daily audit. For each dead/expired API key, search for:
        1. How to refresh/renew the key
        2. Send Ajay a direct renewal link via Telegram

        Reads dead keys from environment variables (401/403 status services).
        """
        log.info("[APIDiscovery] Running dead API check and alert...")

        # Known services that may have expired/invalid keys — check env for placeholders
        services_to_check = {
            "OPENAI_API_KEY":    "OpenAI",
            "ANTHROPIC_API_KEY": "Anthropic Claude",
            "XAI_API_KEY":       "xAI Grok",
            "GROQ_API_KEY":      "Groq",
            "HUGGINGFACE_API_KEY": "HuggingFace",
        }

        dead_services = []
        for env_var, service_name in services_to_check.items():
            key = os.getenv(env_var, "").strip()
            if not key or key.startswith("placeholder") or key.startswith("your_"):
                dead_services.append((env_var, service_name))

        if not dead_services:
            log.info("[APIDiscovery] No obviously dead API keys detected")
            return

        for env_var, service_name in dead_services:
            log.info(f"[APIDiscovery] Searching renewal guide for dead key: {env_var} ({service_name})")

            renewal_query = f"regenerate renew {service_name} API key 2025"
            results = _ddg_search(renewal_query, max_results=4)

            renewal_url = _extract_best_url(results, service_name.split()[0].lower()) if results else ""

            if not renewal_url and results:
                renewal_url = results[0].get("href", "")

            message = (
                f"⚠️ *Dead API Key Detected: {service_name}*\n\n"
                f"`{env_var}` appears to be missing or expired.\n\n"
                f"To renew/replace it:\n"
                f"{'🔗 ' + renewal_url if renewal_url else '📚 Search: ' + service_name + ' API key renewal'}\n\n"
                f"_Reply with the new key or use /setkey {env_var} <value>_"
            )

            _send_telegram(message)
            log.info(f"[APIDiscovery] Sent renewal alert for {service_name}")
