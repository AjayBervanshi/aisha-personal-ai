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
from typing import Optional
from dataclasses import dataclass, field

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

    def mark_failure(self):
        self.failures += 1
        self.last_failure = time.time()
        # Exponential backoff: 1min → 5min → 15min
        backoff = min(60 * (2 ** min(self.failures - 1, 4)), 900)
        self.cooldown_until = time.time() + backoff
        log.warning(f"[{self.name}] Failed #{self.failures}. Cooling down {backoff}s.")

    def mark_success(self):
        self.calls += 1
        self.failures = 0  # Reset on success
        self.cooldown_until = 0.0


class AIRouter:
    """
    Routes AI calls through a waterfall of free providers.
    Handles failures silently and switches automatically.
    """

    def __init__(self):
        self._stats = {
            "gemini":  ProviderStats("Gemini"),
            "groq":    ProviderStats("Groq"),
            "mistral": ProviderStats("Mistral"),
            "ollama":  ProviderStats("Ollama"),
        }
        self._clients = {}
        self._init_clients()

    def _init_clients(self):
        """Initialize available AI clients."""
        # Gemini
        try:
            import google.generativeai as genai
            key = os.getenv("GEMINI_API_KEY", "")
            if key and "your_" not in key:
                genai.configure(api_key=key)
                self._clients["gemini"] = genai.GenerativeModel("gemini-1.5-flash")
                log.info("✅ Gemini initialized")
        except Exception as e:
            log.warning(f"Gemini init failed: {e}")

        # Groq
        try:
            from groq import Groq
            key = os.getenv("GROQ_API_KEY", "")
            if key and "your_" not in key:
                self._clients["groq"] = Groq(api_key=key)
                log.info("✅ Groq initialized")
        except Exception as e:
            log.warning(f"Groq init failed: {e}")

        # Mistral (optional)
        try:
            from mistralai.client import MistralClient
            key = os.getenv("MISTRAL_API_KEY", "")
            if key and "your_" not in key:
                self._clients["mistral"] = MistralClient(api_key=key)
                log.info("✅ Mistral initialized")
        except Exception:
            pass  # Optional — no warning

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
        history: list = None
    ) -> AIResult:
        """
        Try each provider in order. Return first successful response.
        """
        order = ["gemini", "groq", "mistral", "ollama"]
        history = history or []

        for provider in order:
            if provider not in self._clients:
                continue
            stats = self._stats[provider]
            if stats.is_cooling_down():
                remaining = int(stats.cooldown_until - time.time())
                log.info(f"[{provider}] Skipping — cooling down ({remaining}s left)")
                continue

            try:
                start = time.time()
                result = self._call_provider(provider, system_prompt, user_message, history)
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
                log.warning(f"[{provider}] ❌ Failed: {type(e).__name__}: {str(e)[:100]}")
                stats.mark_failure()
                continue  # Try next provider

        # All providers failed
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
        history: list
    ) -> str:
        """Call a specific provider and return text."""

        if provider == "gemini":
            return self._call_gemini(system_prompt, user_message, history)
        elif provider == "groq":
            return self._call_groq(system_prompt, user_message, history)
        elif provider == "mistral":
            return self._call_mistral(system_prompt, user_message, history)
        elif provider == "ollama":
            return self._call_ollama(system_prompt, user_message, history)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    # ── Provider implementations ──────────────────────────────

    def _call_gemini(self, system_prompt, user_message, history) -> str:
        model = self._clients["gemini"]

        # Build history for Gemini format
        gemini_history = []
        for msg in history[-10:]:
            role = "model" if msg["role"] == "assistant" else "user"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=gemini_history)
        full_prompt = f"{system_prompt}\n\n---\n\nAjay says: {user_message}"
        response = chat.send_message(full_prompt)
        return response.text

    def _call_groq(self, system_prompt, user_message, history) -> str:
        client = self._clients["groq"]
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-8:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=messages,
            max_tokens=1024,
            temperature=0.88
        )
        return response.choices[0].message.content

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
            "gemini":  "gemini-1.5-flash",
            "groq":    "llama3-70b-8192",
            "mistral": "mistral-small",
            "ollama":  "llama3-local",
        }
        return names.get(provider, "unknown")

    def _fallback_message(self) -> str:
        return (
            "Arre Ajay, all my AI brains are taking a nap right now 😴\n"
            "Give me a minute and try again? I promise I'll be back! 💜"
        )

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
