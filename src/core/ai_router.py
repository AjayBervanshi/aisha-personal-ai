"""
ai_router.py
============
Smart AI Router — auto-switches between free AI providers.
Order: Gemini → Groq/Llama3 → Mistral → Ollama (local)

If one fails or hits quota, silently falls back to the next.
Aisha never goes down because one API is tired.
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

# Load .env from project root so AIRouter works standalone
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

log = logging.getLogger("Aisha.AIRouter")


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

    def mark_failure(self, is_rate_limit=False, retry_after=0):
        self.failures += 1
        self.last_failure = time.time()
        if is_rate_limit and retry_after > 0:
            # For rate limits: wait exactly what the API tells us (usually 18-60s)
            self.cooldown_until = time.time() + min(retry_after, 90)
            log.warning(f"[{self.name}] Rate limited. Waiting {retry_after}s.")
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
        # Alert tracking — keys are "provider:error_type", values are last notify timestamps
        self._alert_notified: dict = {}
        self._alert_cooldown_secs = 6 * 3600  # Re-alert max once per 6 hours per event
        self._init_clients()

    def _init_clients(self):
        """Initialize available AI clients."""
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

        # OpenAI (ChatGPT)
        try:
            from openai import OpenAI
            key = os.getenv("OPENAI_API_KEY", "")
            if key and "your_" not in key:
                self._clients["openai"] = OpenAI(api_key=key)
                log.info("✅ OpenAI (ChatGPT) initialized")
        except Exception as e:
            log.warning(f"OpenAI init failed: {e}")

        # Claude (Anthropic)
        try:
            from anthropic import Anthropic
            key = os.getenv("ANTHROPIC_API_KEY", "")
            if key and "your_" not in key:
                self._clients["anthropic"] = Anthropic(api_key=key)
                log.info("✅ Claude (Anthropic) initialized")
        except Exception as e:
            log.warning(f"Claude init failed: {e}")

        # Groq (ultra-fast Llama)
        try:
            from groq import Groq
            key = os.getenv("GROQ_API_KEY", "")
            if key and "your_" not in key:
                self._clients["groq"] = Groq(api_key=key)
                log.info("✅ Groq initialized")
        except Exception as e:
            log.warning(f"Groq init failed: {e}")

        # xAI (Grok) — uses OpenAI-compatible API
        try:
            from openai import OpenAI
            key = os.getenv("XAI_API_KEY", "")
            if key and "your_" not in key:
                self._clients["xai"] = OpenAI(api_key=key, base_url="https://api.x.ai/v1")
                log.info("✅ xAI (Grok) initialized")
        except Exception as e:
            log.warning(f"xAI init failed: {e}")

        # Mistral (optional)
        try:
            from mistralai.client import MistralClient
            key = os.getenv("MISTRAL_API_KEY", "")
            if key and "your_" not in key:
                self._clients["mistral"] = MistralClient(api_key=key)
                log.info("✅ Mistral initialized")
        except Exception:
            pass  # Optional — no warning

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

        # Ollama (local — no key needed!)
        try:
            import requests
            r = requests.get("http://localhost:11434/api/tags", timeout=2)
            if r.status_code == 200:
                self._clients["ollama"] = True  # Just a flag
                log.info("✅ Ollama (local) detected")
        except Exception:
            pass  # Not running locally

    # ── Main call ─────────────────────────────────────────────

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        history: list = None,
        image_bytes: bytes = None,
        preferred_provider: str = None,
        nvidia_task_type: str = "chat"
    ) -> AIResult:
        """
        Try each provider in order. Return first successful response.
        For rate limits: wait briefly and retry instead of giving up.
        """
        if image_bytes:
            order = ["gemini", "anthropic", "openai"]  # Only providers with Vision
        else:
            order = ["gemini", "groq", "nvidia", "anthropic", "xai", "openai", "mistral", "ollama"]
            
        if preferred_provider and preferred_provider in self._clients:
            # Move preferred to the front if it's not already there
            if preferred_provider in order:
                order.remove(preferred_provider)
            order.insert(0, preferred_provider)
            
        history = history or []

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
                    or "invalid_api_key" in error_str.lower()
                    or "invalid x-api-key" in error_str.lower()
                    or "Incorrect API key" in error_str
                    or "unpaid invoice" in error_str.lower()
                )

                # Try to extract retry_delay from error
                retry_after = 0
                if is_rate_limit:
                    import re
                    delay_match = re.search(r'seconds:\s*(\d+)', error_str)
                    if delay_match:
                        retry_after = int(delay_match.group(1))
                    else:
                        retry_after = 30  # Default 30s for rate limits

                log.warning(f"[{provider}] ❌ Failed: {type(e).__name__}: {error_str[:150]}")
                stats.mark_failure(is_rate_limit=is_rate_limit, retry_after=retry_after)

                # Send alert email — key expired or quota hit (rate-limited to once per 6h)
                if is_key_expired:
                    # Determine next working provider for the email body
                    remaining = [p for p in order if p != provider and p in self._clients and not self._stats[p].is_cooling_down()]
                    next_provider = remaining[0] if remaining else "NVIDIA fallback pool"
                    self._notify_provider_failure(provider, "key_expired", next_provider)
                elif is_rate_limit and retry_after > 3600:
                    # Only alert for long outages (quota exhausted for the day), not brief rate limits
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

        # Truly all providers exhausted — send critical alert and return fallback message
        self._notify_provider_failure("all", "all_down", "none")
        return AIResult(
            text=self._fallback_message(),
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
                elif resp.status_code == 429:
                    log.warning(f"[Gemini] {model} quota exhausted. Trying next model.")
                    continue
                elif resp.status_code == 404:
                    log.warning(f"[Gemini] {model} not found/deprecated. Skipping.")
                    continue
                else:
                    raise Exception(f"Gemini {model} returned {resp.status_code}: {resp.text[:150]}")
            except requests.exceptions.ConnectionError as e:
                raise Exception(f"Gemini network error: {e}")

        raise Exception("All Gemini models exhausted quota.")

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
        for msg in history[-8:]:
            role = "assistant" if msg["role"] == "model" else msg["role"]
            messages.append({"role": role, "content": msg["content"]})
            
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
        for msg in history[-8:]:
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
        for msg in history[-8:]:
            role = "assistant" if msg["role"] in ("model", "assistant") else "user"
            messages.append({"role": role, "content": msg["content"]})
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
            history=history,
        )

    def _call_mistral(self, system_prompt, user_message, history) -> str:
        from mistralai.models.chat_completion import ChatMessage
        client = self._clients["mistral"]
        messages = [ChatMessage(role="system", content=system_prompt)]
        for msg in history[-6:]:
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
                *[{"role": m["role"], "content": m["content"]} for m in history[-6:]],
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

    def _should_alert(self, key: str) -> bool:
        """True if enough time has passed since last alert for this event key."""
        return (time.time() - self._alert_notified.get(key, 0)) > self._alert_cooldown_secs

    def _notify_provider_failure(self, provider: str, error_type: str, current_fallback: str):
        """
        Send an email alert when a provider key expires, quota is hit, or all providers are down.
        Rate-limited to once per 6 hours per event to avoid inbox spam.
        """
        alert_key = f"{provider}:{error_type}"
        if not self._should_alert(alert_key):
            log.debug(f"[Alert] Suppressed duplicate alert: {alert_key}")
            return
        self._alert_notified[alert_key] = time.time()

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

    def _fallback_message(self) -> str:
        return (
            "Arre Ajay, all my AI brains are taking a nap right now 😴\n"
            "Give me a minute and try again? I promise I'll be back! 💜"
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
        order = ["gemini", "groq", "nvidia", "anthropic", "xai", "openai", "mistral", "ollama"]
        provider_labels = {
            "gemini":    f"Gemini {getattr(self, '_gemini_model_name', '2.5-flash')}",
            "groq":      "Groq llama-3.3-70b",
            "nvidia":    "NVIDIA NIM Pool",
            "anthropic": "Claude (Anthropic)",
            "xai":       "xAI Grok-2",
            "openai":    "OpenAI GPT-4o",
            "mistral":   "Mistral",
            "ollama":    "Ollama (local)",
        }
        role_labels = {
            "gemini":    "primary",
            "groq":      "fallback #1",
            "nvidia":    "fallback #2",
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
        return {
            name: {
                "available": name in self._clients,
                "cooling_down": stats.is_cooling_down(),
                "calls": stats.calls,
                "failures": stats.failures,
            }
            for name, stats in self._stats.items()
        }
