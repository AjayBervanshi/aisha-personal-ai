"""
ai_router.py
============
Smart AI Router — auto-switches between free AI providers.
Order: Gemini → Groq/Llama3 → Mistral → Ollama (local)

If one fails or hits quota, silently falls back to the next.
Aisha never goes down because one API is tired.
"""

import os
import re
import sys
import time
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

# Ensure UTF-8 output on Windows (prevents UnicodeEncodeError with emoji in log lines)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Load .env from project root so AIRouter works standalone
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

log = logging.getLogger("Aisha.AIRouter")


def _log_to_db(level: str, module: str, message: str, details=None):
    """Write a row to aisha_system_log. Never raises — silently swallows errors."""
    try:
        import requests as _req
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            return
        _req.post(
            f"{url}/rest/v1/aisha_system_log",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={"level": level, "module": module, "message": message, "details": details},
            timeout=3,
        )
    except Exception:
        pass  # Never crash the main flow for logging


# Module-level alert timestamps — survive across AIRouter instances within a process.
# IMPORTANT: these are module-level so Render redeploys/restarts do NOT reset the
# 24-hour cooldown and re-send quota emails on every boot.
_last_all_down_alert: float = 0.0       # Rate-limit all-down email to once per 1 hour
_last_quota_alert: dict = {}            # Per-provider quota alert: once per 24 hours
_alert_notified: dict = {}             # Per event-key alert timestamps (module-level, not per-instance)

# Patterns for discovering alternative keys per provider from .env
_PROVIDER_KEY_PATTERNS: dict = {
    "gemini":    ["GEMINI_API_KEY", "GEMINI_KEY_", "GOOGLE_API_KEY"],
    "groq":      ["GROQ_API_KEY", "GROQ_KEY_"],
    "openai":    ["OPENAI_API_KEY", "OPENAI_KEY_"],
    "xai":       ["XAI_API_KEY", "XAI_KEY_"],
    "anthropic": ["ANTHROPIC_API_KEY", "ANTHROPIC_KEY_"],
    # nvidia: handled by nvidia_pool.py — skip
}

_PLACEHOLDER_MARKERS = ("your_", "placeholder", "xxxxxxx", "example", "test_key", "hf_fKAS")


def _normalize_roles(messages: list) -> list:
    """
    Normalize message roles for OpenAI-compatible APIs (Groq, Mistral, xAI, OpenAI, NVIDIA).
    Replaces any 'model' role (used by Gemini) with 'assistant', which is the only
    role these APIs accept besides 'system' and 'user'.
    """
    return [
        {**m, "role": "assistant" if m.get("role") == "model" else m.get("role", "user")}
        for m in messages
    ]


def _find_backup_key(provider: str, current_key: str) -> "str | None":
    """
    Scan the .env file directly for alternative keys for the given provider.
    Returns the first key that differs from current_key and is not a placeholder.
    Returns None if no backup found or provider is not in the pattern map.
    """
    patterns = _PROVIDER_KEY_PATTERNS.get(provider)
    if not patterns:
        return None

    env_path = Path(__file__).parent.parent.parent / ".env"
    if not env_path.exists():
        return None

    try:
        env_text = env_path.read_text(encoding="utf-8")
    except Exception:
        return None

    found_keys: list = []
    for line in env_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        var_name, _, var_value = line.partition("=")
        var_name = var_name.strip()
        var_value = var_value.strip()

        if not var_value:
            continue
        if any(m in var_value.lower() for m in _PLACEHOLDER_MARKERS):
            continue

        # Check if this var matches any pattern for the provider
        for pat in patterns:
            if var_name == pat or var_name.startswith(pat):
                if var_value != current_key:
                    found_keys.append(var_value)
                break

    return found_keys[0] if found_keys else None


@dataclass
class AIResult:
    text: str
    provider: str
    model: str
    latency_ms: int


@dataclass
class ProviderStats:
    name: str
    calls: int = 0
    failures: int = 0
    last_failure: float = 0.0
    cooldown_until: float = 0.0  # Unix timestamp — skip until this time

    def is_cooling_down(self) -> bool:
        return time.time() < self.cooldown_until

    def mark_failure(self, is_rate_limit=False, retry_after=0, is_auth_error=False):
        self.failures += 1
        self.last_failure = time.time()
        if is_auth_error:
            # Dead key (401/403) — don't retry for 24h, it won't fix itself
            self.cooldown_until = time.time() + 86400
            log.warning(f"[{self.name}] Auth error (401/403) — key dead. Cooling down 24h.")
        elif is_rate_limit and retry_after > 0:
            # For rate limits: honour the retry_after value (can be 30s for brief limits
            # or 3600s for daily quota exhaustion)
            self.cooldown_until = time.time() + min(retry_after, 7200)  # cap at 2h
            log.warning(f"[{self.name}] Rate limited. Cooling down {retry_after}s.")
        else:
            # For real errors: shorter backoff (30s → 60s → 120s max)
            backoff = min(30 * (2 ** min(self.failures - 1, 2)), 120)
            self.cooldown_until = time.time() + backoff
            log.warning(f"[{self.name}] Failed #{self.failures}. Cooling down {backoff}s.")

    def mark_success(self):
        self.calls += 1
        self.failures = 0  # Reset on success
        self.cooldown_until = 0.0


class AIRouter:
    """
    Routes AI calls through a waterfall of free providers.
    Priority: Gemini → OpenAI → Groq → Mistral → Ollama
    """

    def __init__(self):
        self._stats = {
            "gemini":    ProviderStats("Gemini"),
            "anthropic": ProviderStats("Claude"),
            "groq":      ProviderStats("Groq"),
            "xai":       ProviderStats("xAI-Grok"),
            "openai":    ProviderStats("OpenAI"),
            "mistral":   ProviderStats("Mistral"),
            "nvidia":    ProviderStats("NVIDIA-NIM"),
            "ollama":    ProviderStats("Ollama"),
        }
        self._clients = {}
        # Alert tracking — use module-level dict so Render restarts don't reset 24h cooldown
        # self._alert_notified is intentionally NOT defined here; _notify_provider_failure
        # accesses the module-level _alert_notified directly.
        # Gemini defaults (set before _init_clients so AttributeError never happens)
        self._gemini_key: "str | None" = None
        self._gemini_model_name: str = "gemini-2.5-flash"
        self._gemini_fallback_models: list = []
        self._init_clients()

    def _init_gemini(self):
        # Gemini — direct REST API via requests (avoids httpx/DNS issues on Windows)
        try:
            import requests as _req
            key = os.getenv("GEMINI_API_KEY", "")
            if key and "your_" not in key:
                self._gemini_key = key
                self._gemini_model_name = os.getenv("AI_MODEL_GEMINI", "gemini-2.5-flash")
                # Multi-model fallback chain — env var OR hardcoded safe list
                fallback_env = os.getenv("AI_MODEL_GEMINI_FALLBACK", "")
                self._gemini_fallback_models = [m.strip() for m in fallback_env.split(",") if m.strip()] or [
                    "gemini-2.0-flash",           # 1500 req/day free — much higher quota
                    "gemini-2.0-flash-lite",      # Fastest + highest quota free tier
                    "gemini-1.5-flash",           # Stable fallback
                    "gemini-1.5-flash-8b",        # Smallest, near-unlimited free
                ]
                # Quick connectivity check (200 = ok, 429 = quota but key valid)
                test_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
                r = _req.get(test_url, timeout=8)
                if r.status_code in (200, 429):
                    self._clients["gemini"] = "rest"
                    log.info(f"Gemini REST initialized: {self._gemini_model_name}")
                else:
                    log.warning(f"Gemini key check failed: {r.status_code}")
        except Exception as e:
            log.warning(f"Gemini init failed: {e}")

    def _init_openai(self):
        # OpenAI (ChatGPT)
        try:
            from openai import OpenAI
            key = os.getenv("OPENAI_API_KEY", "")
            if key and "your_" not in key:
                self._clients["openai"] = OpenAI(api_key=key)
                log.info("✅ OpenAI (ChatGPT) initialized")
        except Exception as e:
            log.warning(f"OpenAI init failed: {e}")

    def _init_anthropic(self):
        # Claude (Anthropic)
        try:
            from anthropic import Anthropic
            key = os.getenv("ANTHROPIC_API_KEY", "")
            if key and "your_" not in key:
                self._clients["anthropic"] = Anthropic(api_key=key)
                log.info("✅ Claude (Anthropic) initialized")
        except Exception as e:
            log.warning(f"Claude init failed: {e}")

    def _init_xai(self):
        # xAI (Grok) — uses OpenAI-compatible API
        try:
            from openai import OpenAI
            key = os.getenv("XAI_API_KEY", "")
            if key and "your_" not in key:
                self._clients["xai"] = OpenAI(api_key=key, base_url="https://api.x.ai/v1")
                log.info("✅ xAI (Grok) initialized")
        except Exception as e:
            log.warning(f"xAI init failed: {e}")

    def _init_groq(self):
        # Groq (ultra-fast Llama)
        try:
            from groq import Groq
            key = os.getenv("GROQ_API_KEY", "")
            if key and "your_" not in key:
                self._clients["groq"] = Groq(api_key=key)
                log.info("✅ Groq initialized")
        except Exception as e:
            log.warning(f"Groq init failed: {e}")

    def _init_mistral(self):
        # Mistral (optional)
        try:
            from mistralai.client import MistralClient
            key = os.getenv("MISTRAL_API_KEY", "")
            if key and "your_" not in key:
                self._clients["mistral"] = MistralClient(api_key=key)
                log.info("✅ Mistral initialized")
        except Exception:
            pass  # Optional — no warning

    def _init_nvidia(self):
        # NVIDIA NIM Pool (22 keys × 1,000 credits/month = 22,000 total)
        try:
            try:
                from src.core.nvidia_pool import NvidiaPool
            except ImportError:
                from core.nvidia_pool import NvidiaPool
            self._nvidia_pool = NvidiaPool()
            # Mark as available if at least one key loaded
            pool_stats = self._nvidia_pool.get_stats()
            total_available = sum(p["available"] for p in pool_stats.values())
            if total_available > 0:
                self._clients["nvidia"] = "pool"
                log.info(f"NVIDIA NIM Pool initialized ({total_available} keys available)")
            else:
                log.warning("NVIDIA NIM Pool: no keys available")
        except Exception as e:
            log.warning(f"NVIDIA NIM Pool init failed: {e}")

    def _init_ollama(self):
        # Ollama (local — no key needed!)
        try:
            import requests
            r = requests.get("http://localhost:11434/api/tags", timeout=2)
            if r.status_code == 200:
                self._clients["ollama"] = True  # Just a flag
                log.info("✅ Ollama (local) detected")
        except Exception:
            pass  # Not running locally

    def _init_clients(self):
        """Initialize available AI clients."""
        self._init_gemini()
        self._init_openai()
        self._init_anthropic()
        self._init_xai()
        self._init_groq()
        self._init_mistral()
        self._init_nvidia()
        self._init_ollama()

    # ── SDK provider re-init ──────────────────────────────────

    # Providers that use an initialized SDK client stored in self._clients[provider].
    # For these, simply setting self._<provider>_key does nothing — we must re-create
    # the client object with the new key.
    _SDK_PROVIDERS = frozenset({"groq", "xai", "openai", "anthropic", "mistral"})

    def _reinit_provider(self, provider: str, key: str) -> bool:
        """
        Re-create the SDK client for *provider* using *key*.
        Returns True on success, False on failure.
        For REST providers (gemini, nvidia, ollama) this is a no-op — callers
        must update self._gemini_key directly.
        """
        try:
            if provider == "groq":
                from groq import Groq
                self._clients["groq"] = Groq(api_key=key)
            elif provider == "openai":
                from openai import OpenAI
                self._clients["openai"] = OpenAI(api_key=key)
            elif provider == "xai":
                from openai import OpenAI
                self._clients["xai"] = OpenAI(api_key=key, base_url="https://api.x.ai/v1")
            elif provider == "anthropic":
                from anthropic import Anthropic
                self._clients["anthropic"] = Anthropic(api_key=key)
            elif provider == "mistral":
                from mistralai.client import MistralClient
                self._clients["mistral"] = MistralClient(api_key=key)
            else:
                # REST providers: nothing to reinit here
                return False
            log.info(f"[{provider}] SDK client re-initialized with backup key.")
            return True
        except Exception as e:
            log.warning(f"[{provider}] Failed to reinit SDK client with backup key: {e}")
            return False

    # ── Main call ─────────────────────────────────────────────

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        history: list = None,
        image_bytes: bytes = None,
        preferred_provider: str = None,
        nvidia_task_type: str = "chat",
        is_owner: bool = False,
    ) -> AIResult:
        """
        Try each provider in order. Return first successful response.
        For rate limits: wait briefly and retry instead of giving up.
        """
        if image_bytes:
            order = ["gemini", "anthropic", "openai"]  # Only providers with Vision
        else:
            # Gemini 2.5-flash is working (verified 2026-03-26) — best quality for Hindi content
            # NVIDIA NIM is the reliable backstop (22k credits/month, never fails)
            # Dead providers (Groq/OAI/Anthropic/xAI) get 24h cooldown on first 401 and are skipped
            order = ["gemini", "nvidia", "groq", "anthropic", "xai", "openai", "mistral", "ollama"]

        if preferred_provider and preferred_provider in self._clients:
            # Move preferred to the front if it's not already there
            if preferred_provider in order:
                order.remove(preferred_provider)
            order.insert(0, preferred_provider)

        history = history or []
        failed_providers: list = []

        for provider in order:
            if provider not in self._clients:
                continue
            stats = self._stats[provider]
            
            # If cooling down, skip and move to next provider instantly
            if stats.is_cooling_down():
                remaining = int(stats.cooldown_until - time.time())
                log.info(f"[{provider}] Skipping — cooling down ({remaining}s left)")
                continue

            try:
                start = time.time()
                result = self._call_provider(provider, system_prompt, user_message, history, image_bytes, nvidia_task_type=nvidia_task_type)
                latency = int((time.time() - start) * 1000)
                stats.mark_success()
                log.info(f"[{provider}] ✅ Response in {latency}ms")
                _log_to_db("INFO", "ai_router", f"{provider} success in {latency}ms")
                return AIResult(
                    text=result,
                    provider=provider,
                    model=self._model_name(provider),
                    latency_ms=latency
                )

            except Exception as e:
                error_str = str(e)
                is_rate_limit = "429" in error_str or "RATE_LIMIT" in error_str.upper() or "quota" in error_str.lower()
                is_key_expired = (
                    "401" in error_str
                    or "403" in error_str
                    or "invalid_api_key" in error_str.lower()
                    or "invalid x-api-key" in error_str.lower()
                    or "Incorrect API key" in error_str
                    or "unpaid invoice" in error_str.lower()
                    or "authentication_error" in error_str.lower()
                    or "permission" in error_str.lower()
                )

                # ── Auto-discover backup key on 401/403 and retry once ──────
                if is_key_expired and provider != "nvidia":
                    current_key = getattr(self, f"_{provider}_key", None) or os.getenv(
                        f"{provider.upper()}_API_KEY", ""
                    )
                    backup_key = _find_backup_key(provider, current_key)
                    if backup_key:
                        log.info(f"[{provider}] Auth error — found backup key, retrying once.")
                        # Save original state so we can restore on failure
                        _orig_key_attr = f"_{provider}_key"
                        _had_attr = hasattr(self, _orig_key_attr)
                        _orig_val = getattr(self, _orig_key_attr, None) if _had_attr else None
                        _orig_client = self._clients.get(provider)
                        try:
                            if provider in self._SDK_PROVIDERS:
                                # SDK providers (groq, xai, openai, anthropic, mistral) use an
                                # initialized client object — setting self._<provider>_key alone
                                # has no effect.  Re-create the client with the backup key.
                                if not self._reinit_provider(provider, backup_key):
                                    raise RuntimeError(f"Could not reinit {provider} client")
                            else:
                                # REST providers (gemini) only need the key attribute updated
                                if _had_attr:
                                    setattr(self, _orig_key_attr, backup_key)
                            start = time.time()
                            result = self._call_provider(
                                provider, system_prompt, user_message, history, image_bytes,
                                nvidia_task_type=nvidia_task_type
                            )
                            latency = int((time.time() - start) * 1000)
                            stats.mark_success()
                            log.info(f"[{provider}] ✅ Backup key worked — response in {latency}ms")
                            _log_to_db("INFO", "ai_router", f"{provider} backup key success in {latency}ms")
                            return AIResult(
                                text=result,
                                provider=provider,
                                model=self._model_name(provider),
                                latency_ms=latency
                            )
                        except Exception as backup_err:
                            log.warning(f"[{provider}] Backup key also failed: {backup_err}")
                            # Restore original state (key attr + SDK client)
                            if _had_attr and _orig_val is not None:
                                setattr(self, _orig_key_attr, _orig_val)
                            if _orig_client is not None:
                                self._clients[provider] = _orig_client
                            # Fall through to mark_failure below

                # Try to extract retry_delay from error
                retry_after = 0
                if is_rate_limit:
                    # Check for explicit retry_after=N in error message
                    explicit_match = re.search(r'retry_after=(\d+)', error_str)
                    if explicit_match:
                        retry_after = int(explicit_match.group(1))
                    else:
                        delay_match = re.search(r'seconds:\s*(\d+)', error_str)
                        if delay_match:
                            retry_after = int(delay_match.group(1))
                        else:
                            retry_after = 30  # Default 30s for brief rate limits

                log.warning(f"[{provider}] Failed: {type(e).__name__}: {error_str[:150]}")
                failed_providers.append(provider)
                stats.mark_failure(
                    is_rate_limit=is_rate_limit,
                    retry_after=retry_after,
                    is_auth_error=is_key_expired
                )

                # ── Alert emails — key expired or quota hit ──────────────────
                if is_key_expired:
                    remaining = [p for p in order if p != provider and p in self._clients and not self._stats[p].is_cooling_down()]
                    next_provider = remaining[0] if remaining else "NVIDIA fallback pool"
                    self._notify_provider_failure(provider, "key_expired", next_provider)
                elif is_rate_limit and retry_after > 3600:
                    # Long-duration quota exhaustion alert
                    remaining = [p for p in order if p != provider and p in self._clients and not self._stats[p].is_cooling_down()]
                    next_provider = remaining[0] if remaining else "NVIDIA fallback pool"
                    self._notify_provider_failure(provider, "quota_exhausted", next_provider)
                elif is_rate_limit and provider == order[0]:
                    # Primary provider hit quota (even brief) — send 24h-rate-limited warning
                    global _last_quota_alert
                    last_sent = _last_quota_alert.get(provider, 0.0)
                    if (time.time() - last_sent) > 86400:
                        _last_quota_alert[provider] = time.time()
                        remaining = [p for p in order if p != provider and p in self._clients and not self._stats[p].is_cooling_down()]
                        next_provider = remaining[0] if remaining else "NVIDIA fallback pool"
                        self._notify_provider_failure(provider, "quota_exhausted", next_provider)

                continue  # Try next provider

        # ── Last-resort NVIDIA fallback — try all pools before giving up ──────
        # This runs when ALL named providers above failed. Uses NVIDIA general/fast
        # pools which have models not in the normal rotation.
        if "nvidia" in self._clients:
            for last_resort_pool in ("general", "fast", "chat"):
                try:
                    start = time.time()
                    result = self._call_nvidia(system_prompt, user_message, history or [], task_type=last_resort_pool)
                    latency = int((time.time() - start) * 1000)
                    log.info(f"[NVIDIA-LastResort] ✅ {last_resort_pool} pool responded in {latency}ms")
                    return AIResult(text=result, provider="nvidia", model=f"nvidia-{last_resort_pool}", latency_ms=latency)
                except Exception:
                    continue

        # Truly all providers exhausted — send critical alert (rate-limited to once per 1 hour)
        global _last_all_down_alert
        if (time.time() - _last_all_down_alert) > 3600:
            _last_all_down_alert = time.time()
            self._notify_provider_failure("all", "all_down", "none")
        else:
            log.warning("[AIRouter] All providers down — all-down alert suppressed (sent < 1h ago)")
        return AIResult(
            text=self._fallback_message(failed_providers=failed_providers, is_owner=is_owner),
            provider="fallback",
            model="none",
            latency_ms=0
        )

    def _call_provider(
        self,
        provider: str,
        system_prompt: str,
        user_message: str,
        history: list,
        image_bytes: bytes = None,
        nvidia_task_type: str = "writing"
    ) -> str:
        """Call a specific provider and return text."""

        if provider == "gemini":
            return self._call_gemini(system_prompt, user_message, history, image_bytes)
        elif provider == "anthropic":
            return self._call_anthropic(system_prompt, user_message, history, image_bytes)
        elif provider == "openai":
            return self._call_openai(system_prompt, user_message, history, image_bytes)
        elif provider == "groq":
            return self._call_groq(system_prompt, user_message, history)
        elif provider == "xai":
            return self._call_xai(system_prompt, user_message, history)
        elif provider == "mistral":
            return self._call_mistral(system_prompt, user_message, history)
        elif provider == "nvidia":
            return self._call_nvidia(system_prompt, user_message, history, task_type=nvidia_task_type)
        elif provider == "ollama":
            return self._call_ollama(system_prompt, user_message, history)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    # ── Provider implementations ──────────────────────────────

    def _call_gemini(self, system_prompt, user_message, history, image_bytes: bytes = None) -> str:
        """Call Gemini via direct REST API (avoids httpx/DNS issues on Windows)."""
        import requests, json, base64

        # Build prompt with history
        if history:
            hist_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in history[-6:]])
            full_prompt = f"{system_prompt}\n\nRecent conversation:\n{hist_text}\n\n---\n\nAjay says: {user_message}"
        else:
            full_prompt = f"{system_prompt}\n\n---\n\nAjay says: {user_message}"

        parts = [{"text": full_prompt}]
        if image_bytes:
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": base64.b64encode(image_bytes).decode("utf-8")
                }
            })

        payload = {"contents": [{"parts": parts}]}

        all_models = [self._gemini_model_name] + self._gemini_fallback_models
        for model in all_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self._gemini_key}"
            try:
                resp = requests.post(url, json=payload, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    log.info(f"[Gemini] Responded via {model}")
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                elif resp.status_code in [401, 403]:
                    log.error(f"[Gemini] {model} authentication failed (401/403). Forcing fallback.")
                    # Break loop so it throws the Exception outside and the Router fails over to NVIDIA
                    raise Exception(f"invalid_api_key Gemini returned {resp.status_code}: {resp.text[:100]}")
                elif resp.status_code == 429:
                    log.warning(f"[Gemini] {model} quota exhausted. Trying next model.")
                    continue
                elif resp.status_code == 404:
                    log.warning(f"[Gemini] {model} not found/deprecated. Skipping.")
                    continue
                else:
                    log.warning(f"[Gemini] {model} returned {resp.status_code}. Trying next model.")
                    continue
            except requests.exceptions.RequestException as e:
                log.error(f"[Gemini] HTTP request failed for {model}: {e}")
                continue

        # If we exit the loop without returning, all models failed. Throw exception to trigger AIRouter fallback.
        raise Exception("All Gemini models failed or exhausted quota. retry_after=3600")

    def _call_anthropic(self, system_prompt, user_message, history, image_bytes: bytes = None) -> str:
        """
        Claude Opus 4.6 with adaptive thinking + streaming.
        - Adaptive thinking: Claude decides how much to reason internally
        - Streaming: prevents timeout on long story scripts (8-15 min narration)
        - 128K max_tokens: enough for full Hindi story scripts
        """
        client = self._clients["anthropic"]
        messages = []
        for msg in history[-8:]:
            role = "assistant" if msg["role"] in ("model", "assistant") else "user"
            messages.append({"role": role, "content": msg["content"]})

        content = [{"type": "text", "text": user_message}]
        if image_bytes:
            import base64
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.b64encode(image_bytes).decode("utf-8"),
                }
            })

        messages.append({"role": "user", "content": content})

        # Detect if this is a long-form creative task (story script generation)
        is_long_form = any(kw in user_message.lower() for kw in [
            "script", "story", "kahani", "episode", "chapter", "narrat", "write"
        ])

        try:
            # Use streaming for long-form content to avoid HTTP timeouts
            if is_long_form:
                with client.messages.stream(
                    model="claude-opus-4-6",
                    max_tokens=128000,
                    thinking={"type": "adaptive"},
                    system=system_prompt,
                    messages=messages,
                ) as stream:
                    final = stream.get_final_message()
                    for block in final.content:
                        if block.type == "text":
                            return block.text
                    return final.content[0].text
            else:
                response = client.messages.create(
                    model="claude-opus-4-6",
                    max_tokens=16000,
                    thinking={"type": "adaptive"},
                    system=system_prompt,
                    messages=messages,
                )
                # Extract text (skip thinking blocks)
                for block in response.content:
                    if block.type == "text":
                        return block.text
                return response.content[0].text

        except Exception as e:
            # Fall back to Sonnet 4.6 if Opus quota is hit
            if "529" in str(e) or "overloaded" in str(e).lower():
                log.warning("[Claude] Opus overloaded, falling back to Sonnet 4.6")
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=16000,
                    thinking={"type": "adaptive"},
                    system=system_prompt,
                    messages=messages,
                )
                for block in response.content:
                    if block.type == "text":
                        return block.text
            raise

    def _call_openai(self, system_prompt, user_message, history, image_bytes: bytes = None) -> str:
        client = self._clients["openai"]
        messages = [{"role": "system", "content": system_prompt}]
        for msg in _normalize_roles(history[-8:]):
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        content = [{"type": "text", "text": user_message}]
        if image_bytes:
            import base64
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
                }
            })
            
        messages.append({"role": "user", "content": content})

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=16000,
            temperature=0.88
        )
        return response.choices[0].message.content

    def _call_groq(self, system_prompt, user_message, history) -> str:
        client = self._clients["groq"]
        messages = [{"role": "system", "content": system_prompt}]
        for msg in _normalize_roles(history[-8:]):
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=32000,  # Groq supports huge context
            temperature=0.88
        )
        return response.choices[0].message.content

    def _call_xai(self, system_prompt, user_message, history) -> str:
        """xAI Grok — uses OpenAI-compatible API."""
        client = self._clients["xai"]
        messages = [{"role": "system", "content": system_prompt}]
        for msg in _normalize_roles(history[-8:]):
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        model = os.getenv("AI_MODEL_XAI", "grok-2-latest")
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=16000,
            temperature=0.88
        )
        return response.choices[0].message.content

    def _call_nvidia(self, system_prompt, user_message, history, task_type: str = "chat") -> str:
        """NVIDIA NIM Pool — 22 keys × 1,000 credits/month = 22,000 total credits."""
        return self._nvidia_pool.generate(
            task_type=task_type,
            system_prompt=system_prompt,
            user_message=user_message,
            history=_normalize_roles(history),
        )

    def _call_mistral(self, system_prompt, user_message, history) -> str:
        from mistralai.models.chat_completion import ChatMessage
        client = self._clients["mistral"]
        messages = [ChatMessage(role="system", content=system_prompt)]
        for msg in _normalize_roles(history[-6:]):
            messages.append(ChatMessage(role=msg["role"], content=msg["content"]))
        messages.append(ChatMessage(role="user", content=user_message))

        response = client.chat(
            model="mistral-small-latest",
            messages=messages,
            max_tokens=1024
        )
        return response.choices[0].message.content

    def _call_ollama(self, system_prompt, user_message, history) -> str:
        import requests, json
        payload = {
            "model": "llama3",  # Or whatever model you have installed
            "messages": [
                {"role": "system", "content": system_prompt},
                *[{"role": m["role"], "content": m["content"]} for m in _normalize_roles(history[-6:])],
                {"role": "user", "content": user_message}
            ],
            "stream": False
        }
        r = requests.post(
            "http://localhost:11434/api/chat",
            json=payload,
            timeout=60
        )
        return r.json()["message"]["content"]

    # ── Helpers ───────────────────────────────────────────────

    def _model_name(self, provider: str) -> str:
        names = {
            "gemini":    getattr(self, '_gemini_model_name', 'gemini-2.5-pro'),
            "anthropic": "claude-opus-4-6",
            "groq":      "llama-3.3-70b-versatile",
            "xai":       "grok-2-latest",
            "openai":    "gpt-4o",
            "mistral":   "mistral-large-latest",
            "nvidia":    "qwen/qwen3.5-122b-a10b",
            "ollama":    "llama3-local",
        }
        return names.get(provider, "unknown")

    # ── Alert system ──────────────────────────────────────────

    def _should_alert(self, key: str, error_type: str = "") -> bool:
        """True if enough time has passed since last alert for this event key.
        Cooldowns: quota_exhausted=24h (Gemini daily quota resets at midnight),
                   key_expired=6h, all_down=1h."""
        cooldown = {
            "quota_exhausted": 86400,   # 24 hours — Gemini quota resets daily
            "key_expired":     21600,   # 6 hours
            "all_down":        3600,    # 1 hour
        }.get(error_type, 21600)
        return (time.time() - _alert_notified.get(key, 0)) > cooldown

    def _notify_provider_failure(self, provider: str, error_type: str, current_fallback: str):
        """
        Send an email alert when a provider key expires, quota is hit, or all providers are down.
        Uses module-level _alert_notified so Render restarts don't reset the cooldown.
        quota_exhausted: once per 24h (Gemini daily limit resets at midnight UTC).
        """
        alert_key = f"{provider}:{error_type}"
        _log_to_db("ERROR", "ai_router", f"{provider} failed: {error_type}",
                   details={"provider": provider, "error_type": error_type, "fallback": current_fallback})
        if not self._should_alert(alert_key, error_type):
            log.debug(f"[Alert] Suppressed duplicate alert: {alert_key}")
            return
        _alert_notified[alert_key] = time.time()

        provider_upper = provider.upper()
        subjects = {
            "key_expired":      f"[Aisha] {provider_upper} API key expired — action needed",
            "quota_exhausted":  f"[Aisha] {provider_upper} daily quota hit — using {current_fallback}",
            "all_down":         "[Aisha] ⚠️ CRITICAL: All AI providers down",
        }
        bodies = {
            "key_expired": (
                f"Aisha here, Ajay.\n\n"
                f"The {provider_upper} API key has expired or is invalid (401 error).\n\n"
                f"Currently falling back to: {current_fallback.upper()}\n\n"
                f"Action needed:\n"
                f"  1. Go to the {provider_upper} dashboard and generate a new API key\n"
                f"  2. Update your .env file: {provider_upper}_API_KEY=<new_key>\n"
                f"  3. Restart Aisha\n\n"
                f"Until fixed, I'll keep using {current_fallback} so content keeps flowing."
            ),
            "quota_exhausted": (
                f"Aisha here, Ajay.\n\n"
                f"{provider_upper} has hit its daily free-tier quota (429 / RESOURCE_EXHAUSTED).\n\n"
                f"Currently falling back to: {current_fallback.upper()}\n\n"
                f"Quota resets automatically at midnight UTC — no action needed.\n"
                f"If this happens daily, consider upgrading {provider_upper} to a paid plan\n"
                f"or set AI_MODEL_GEMINI=gemini-2.0-flash in .env (higher quota, same quality)."
            ),
            "all_down": (
                f"Aisha here — CRITICAL ALERT, Ajay.\n\n"
                f"ALL primary AI providers are currently failing.\n\n"
                f"Provider status:\n{self._get_provider_status_text()}\n\n"
                f"I am running on the NVIDIA last-resort fallback pool.\n"
                f"Please check your API keys and internet connection."
            ),
        }

        subject = subjects.get(error_type, f"[Aisha] {provider_upper} AI error")
        body = bodies.get(error_type, f"Provider {provider_upper} failed: {error_type}")

        try:
            from src.core.gmail_engine import GmailEngine
            from src.core.config import GMAIL_USER
            if GMAIL_USER:
                gmail = GmailEngine()
                gmail.send_email(GMAIL_USER, subject, body)
                log.info(f"[Alert] Email sent: {alert_key}")
            else:
                log.warning(f"[Alert] GMAIL_USER not set — cannot send: {subject}")
        except Exception as e:
            log.warning(f"[Alert] Failed to send alert email: {e}")

    def _get_provider_status_text(self) -> str:
        """Build a human-readable provider status summary for alert emails."""
        lines = []
        for name, stats in self._stats.items():
            if name not in self._clients:
                status = "NOT CONFIGURED"
            elif stats.is_cooling_down():
                remaining = int(stats.cooldown_until - time.time())
                status = f"COOLING DOWN ({remaining}s)"
            elif stats.failures > 0:
                status = f"DEGRADED ({stats.failures} failures)"
            else:
                status = "OK"
            lines.append(f"  {name.upper():<12} {status}")
        return "\n".join(lines)

    def _fallback_message(self, failed_providers: list = None, is_owner: bool = False) -> str:
        """Return a user-appropriate message when all AI providers are exhausted.

        - Owner (Ajay): shows which providers failed + that NVIDIA fallback was tried.
        - Non-owner: generic temporary-issue message, no technical details exposed.
        """
        if is_owner:
            failed_str = (
                ", ".join(failed_providers) if failed_providers else "all configured providers"
            )
            return (
                f"Ajay, all AI providers are temporarily down. "
                f"Failed: {failed_str}. NVIDIA NIM fallback was also exhausted. "
                f"Run /syscheck for details. I'll retry automatically on your next message. 🔧"
            )
        # Generic message for guests — no internal details exposed
        return (
            "I'm having a temporary connection issue — please try again in a moment. "
            "My backup systems are standing by and should recover shortly. 🙏"
        )

    @property
    def available_providers(self) -> list:
        return list(self._clients.keys())

    def get_active_provider(self) -> str:
        """
        Return a human-readable string describing which provider would be used right now.
        Walks the default order and returns the first provider that is configured
        and not cooling down.
        """
        order = ["gemini", "nvidia", "groq", "anthropic", "xai", "openai", "mistral", "ollama"]
        provider_labels = {
            "gemini":    f"Gemini {getattr(self, '_gemini_model_name', '2.5-flash')}",
            "nvidia":    "NVIDIA NIM Pool (22 keys, 22k credits/month)",
            "groq":      "Groq llama-3.3-70b",
            "anthropic": "Claude (Anthropic)",
            "xai":       "xAI Grok",
            "openai":    "OpenAI GPT-4o",
            "mistral":   "Mistral",
            "ollama":    "Ollama (local)",
        }
        role_labels = {
            "gemini":    "primary",
            "nvidia":    "fallback #1",
            "groq":      "fallback #2",
            "anthropic": "fallback #3",
            "xai":       "fallback #4",
            "openai":    "fallback #5",
            "mistral":   "fallback #6",
            "ollama":    "fallback #7",
        }
        for provider in order:
            if provider not in self._clients:
                continue
            if self._stats[provider].is_cooling_down():
                continue
            label = provider_labels.get(provider, provider)
            role = role_labels.get(provider, "fallback")
            return f"{label} ({role})"
        return "None — all providers down"

    def chat(self, message: str, system_prompt: str = None, preferred_provider: str = None) -> str:
        """Simple wrapper — returns just the text string."""
        result = self.generate(
            system_prompt=system_prompt or "You are Aisha, a helpful AI assistant.",
            user_message=message,
            preferred_provider=preferred_provider
        )
        return result.text

    def status(self) -> dict:
        """Return current status of all providers."""
        now = time.time()
        return {
            name: {
                "available": name in self._clients,
                "cooling_down": stats.is_cooling_down(),
                "cooldown_secs_left": max(0, int(stats.cooldown_until - now)) if stats.is_cooling_down() else 0,
                "calls": stats.calls,
                "failures": stats.failures,
            }
            for name, stats in self._stats.items()
        }
