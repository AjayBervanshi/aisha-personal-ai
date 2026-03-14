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
            "ollama":    ProviderStats("Ollama"),
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
                # Try gemini-2.5-pro first, fall back to 2.5-flash then 2.0-flash
                for model_name in ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]:
                    try:
                        self._clients["gemini"] = genai.GenerativeModel(model_name)
                        self._gemini_model_name = model_name
                        log.info(f"Gemini initialized: {model_name}")
                        break
                    except Exception:
                        continue
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
        preferred_provider: str = None
    ) -> AIResult:
        """
        Try each provider in order. Return first successful response.
        For rate limits: wait briefly and retry instead of giving up.
        """
        if image_bytes:
            order = ["gemini", "anthropic", "openai"]  # Only providers with Vision
        else:
            order = ["gemini", "anthropic", "groq", "xai", "openai", "mistral", "ollama"]
            
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
                result = self._call_provider(provider, system_prompt, user_message, history, image_bytes)
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
                
                # We no longer wait and retry. Since we have 6 brains, just fall through 
                # to the next provider instantly to avoid delaying the response.
                
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
        history: list,
        image_bytes: bytes = None
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
        elif provider == "ollama":
            return self._call_ollama(system_prompt, user_message, history)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    # ── Provider implementations ──────────────────────────────

    def _call_gemini(self, system_prompt, user_message, history, image_bytes: bytes = None) -> str:
        # Build history for Gemini format
        gemini_history = []
        for msg in history[-10:]:
            role = "model" if msg["role"] == "assistant" else "user"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        full_prompt = f"{system_prompt}\n\n---\n\nAjay says: {user_message}"
        
        message_parts = [full_prompt]
        if image_bytes:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(image_bytes))
            message_parts.append(img)
            
        import google.generativeai as genai
        try:
            # First try the primary model
            model = genai.GenerativeModel("gemini-2.5-pro")
            chat = model.start_chat(history=gemini_history)
            response = chat.send_message(message_parts)
            return response.text
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(type(e).__name__):
                log.warning(f"[Gemini] Rate limit hit on Pro model. Falling back to Flash model!")
                # Fallback to flash
                model = genai.GenerativeModel("gemini-2.5-flash")
                chat = model.start_chat(history=gemini_history)
                response = chat.send_message(message_parts)
                return response.text
            raise e

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
                    return stream.get_final_message().content[0].text
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

        response = client.chat.completions.create(
            model="grok-2-latest",
            messages=messages,
            max_tokens=16000,
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
            "gemini":    getattr(self, '_gemini_model_name', 'gemini-2.5-pro'),
            "anthropic": "claude-opus-4-6",
            "groq":      "llama-3.3-70b-versatile",
            "xai":       "grok-2-latest",
            "openai":    "gpt-4o",
            "mistral":   "mistral-large-latest",
            "ollama":    "llama3-local",
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
