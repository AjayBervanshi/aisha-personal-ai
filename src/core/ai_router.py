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
import json
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

log = logging.getLogger("Aisha.AIRouter")

@dataclass
class AIResult:
    text: str
    provider: str
    model: str
    latency_ms: int
    tool_calls: Optional[List[Dict[str, Any]]] = None

@dataclass
class ProviderStats:
    name: str
    calls: int = 0
    failures: int = 0
    last_failure: float = 0.0
    cooldown_until: float = 0.0

    def is_cooling_down(self) -> bool:
        return time.time() < self.cooldown_until

    def mark_failure(self, is_rate_limit=False, retry_after=0):
        self.failures += 1
        self.last_failure = time.time()
        if is_rate_limit and retry_after > 0:
            self.cooldown_until = time.time() + min(retry_after, 90)
            log.warning(f"[{self.name}] Rate limited. Waiting {retry_after}s.")
        else:
            backoff = min(30 * (2 ** min(self.failures - 1, 2)), 120)
            self.cooldown_until = time.time() + backoff
            log.warning(f"[{self.name}] Failed #{self.failures}. Cooling down {backoff}s.")

    def mark_success(self):
        self.calls += 1
        self.failures = 0
        self.cooldown_until = 0.0

class AIRouter:
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

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        history: list = None,
        image_bytes: bytes = None,
        tools: list = None
    ) -> AIResult:
        """Try each provider in order. Return first successful response."""
        if image_bytes:
            order = ["gemini", "anthropic", "openai"]
        else:
            order = ["gemini", "openai", "groq", "xai", "anthropic", "mistral", "ollama"]
            
        history = history or []

        for provider in order:
            if provider not in self._clients:
                continue
            stats = self._stats[provider]
            
            if stats.is_cooling_down():
                continue

            try:
                start = time.time()
                result_text, tool_calls = self._call_provider(
                    provider, system_prompt, user_message, history, image_bytes, tools
                )
                latency = int((time.time() - start) * 1000)
                stats.mark_success()

                return AIResult(
                    text=result_text,
                    provider=provider,
                    model=self._model_name(provider),
                    latency_ms=latency,
                    tool_calls=tool_calls
                )

            except Exception as e:
                error_str = str(e)
                is_rate_limit = "429" in error_str or "RATE_LIMIT" in error_str.upper() or "quota" in error_str.lower()
                
                retry_after = 0
                if is_rate_limit:
                    import re
                    delay_match = re.search(r'seconds:\s*(\d+)', error_str)
                    if delay_match:
                        retry_after = int(delay_match.group(1))
                    else:
                        retry_after = 30
                
                log.warning(f"[{provider}] ❌ Failed: {type(e).__name__}: {error_str[:150]}")
                stats.mark_failure(is_rate_limit=is_rate_limit, retry_after=retry_after)
                continue

        return AIResult(
            text=self._fallback_message(),
            provider="fallback",
            model="none",
            latency_ms=0,
            tool_calls=None
        )

    def _call_provider(self, provider: str, system_prompt: str, user_message: str, history: list, image_bytes: bytes = None, tools: list = None) -> Tuple[str, Optional[List[Dict]]]:
        """Returns (text_response, tool_calls_list)"""
        if provider == "gemini":
            return self._call_gemini(system_prompt, user_message, history, image_bytes, tools)
        elif provider == "openai":
            return self._call_openai(system_prompt, user_message, history, image_bytes, tools)
        elif provider == "groq":
            return self._call_groq(system_prompt, user_message, history, tools)
        elif provider == "xai":
            return self._call_xai(system_prompt, user_message, history, tools)
        elif provider == "anthropic":
            return self._call_anthropic(system_prompt, user_message, history, image_bytes)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _call_gemini(self, system_prompt, user_message, history, image_bytes, tools):
        model = self._clients["gemini"]

        # Build history for Gemini format
        gemini_history = []
        for msg in history[-10:]:
            role = "model" if msg["role"] == "assistant" else "user"

            # Handle tool call history properly for Gemini
            parts = []
            if "tool_calls" in msg and msg["tool_calls"]:
                # If assistant made a tool call in history
                for tc in msg["tool_calls"]:
                    parts.append({"function_call": {"name": tc["name"], "args": tc["args"]}})
            elif "tool_result" in msg:
                # If user provided tool result in history
                parts.append({"function_response": {"name": msg["tool_name"], "response": {"result": msg["tool_result"]}}})
            else:
                parts.append(msg["content"])

            gemini_history.append({"role": role, "parts": parts})

        # Format tools for Gemini (convert from OpenAI JSON schema format to Gemini format)
        gemini_tools = None
        if tools:
            gemini_tools = []
            for t in tools:
                if t["type"] == "function":
                    func_data = t["function"]

                    # Convert OpenAI schema to Gemini schema
                    gemini_schema = {
                        "type": "object",
                        "properties": {},
                        "required": func_data.get("parameters", {}).get("required", [])
                    }

                    for prop_name, prop_details in func_data.get("parameters", {}).get("properties", {}).items():
                        gemini_schema["properties"][prop_name] = {
                            "type": prop_details.get("type", "string").upper(),
                            "description": prop_details.get("description", "")
                        }

                    gemini_tools.append({
                        "function_declarations": [
                            {
                                "name": func_data["name"],
                                "description": func_data["description"],
                                "parameters": gemini_schema
                            }
                        ]
                    })

        chat = model.start_chat(history=gemini_history)
        
        message_parts = [f"{system_prompt}\n\n---\n\n{user_message}"]
        if image_bytes:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(image_bytes))
            message_parts.append(img)
            
        try:
            response = chat.send_message(message_parts, tools=gemini_tools)
        except Exception as e:
            # If tool parsing fails due to schema issues, fallback to no-tools call
            log.error(f"[Gemini] Tool call setup failed: {e}. Falling back to standard call.")
            response = chat.send_message(message_parts)
            
        tool_calls = []
        if response.parts:
            for part in response.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    func_call = part.function_call
                    # Extract args
                    args = {}
                    for key, val in func_call.args.items():
                        args[key] = val

                    tool_calls.append({
                        "id": f"call_{func_call.name}",
                        "name": func_call.name,
                        "args": args
                    })

        return response.text, tool_calls if tool_calls else None

    def _call_openai(self, system_prompt, user_message, history, image_bytes, tools):
        client = self._clients["openai"]
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-8:]:
            # Clean up role and handle tool history
            role = "assistant" if msg["role"] == "model" else msg["role"]
            if "tool_result" in msg:
                messages.append({"role": "tool", "tool_call_id": "call_id", "name": msg["tool_name"], "content": msg["tool_result"]})
            else:
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
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1024,
            temperature=0.88,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None
        )

        msg = response.choices[0].message

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "args": json.loads(tc.function.arguments)
                })

        return msg.content or "", tool_calls if tool_calls else None

    def _call_groq(self, system_prompt, user_message, history, tools):
        client = self._clients["groq"]
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-8:]:
            if "tool_result" in msg:
                messages.append({"role": "tool", "tool_call_id": "call_id", "name": msg["tool_name"], "content": msg["tool_result"]})
            else:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=1024,
            temperature=0.88,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None
        )
        msg = response.choices[0].message
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "args": json.loads(tc.function.arguments)
                })
        return msg.content or "", tool_calls if tool_calls else None

    def _call_xai(self, system_prompt, user_message, history, tools):
        client = self._clients["xai"]
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-8:]:
            role = "assistant" if msg["role"] in ("model", "assistant") else "user"
            if "tool_result" in msg:
                messages.append({"role": "tool", "tool_call_id": "call_id", "name": msg["tool_name"], "content": msg["tool_result"]})
            else:
                messages.append({"role": role, "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model="grok-2-latest",
            messages=messages,
            max_tokens=1024,
            temperature=0.88,
            tools=tools if tools else None
        )
        msg = response.choices[0].message
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "args": json.loads(tc.function.arguments)
                })
        return msg.content or "", tool_calls if tool_calls else None

    def _call_anthropic(self, system_prompt, user_message, history, image_bytes):
        # Tools not currently mapped for anthropic in this router, fallback to text
        client = self._clients["anthropic"]
        messages = []
        for msg in history[-8:]:
            role = "assistant" if msg["role"] in ("model", "assistant") else "user"
            # Skip tool traces for anthropic as it requires a specific block structure
            if "tool_result" not in msg and "tool_calls" not in msg:
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

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=system_prompt,
            messages=messages
        )
        return response.content[0].text, None

    def _model_name(self, provider: str) -> str:
        names = {
            "gemini":    "gemini-1.5-flash",
            "anthropic": "claude-3.5-sonnet",
            "groq":      "llama-3.3-70b",
            "xai":       "grok-2-latest",
            "openai":    "gpt-4o-mini",
            "mistral":   "mistral-small",
            "ollama":    "llama3-local",
        }
        return names.get(provider, "unknown")

    def _fallback_message(self) -> str:
        return (
            "Arre Ajay, all my AI brains are taking a nap right now 😴\n"
            "Give me a minute and try again? I promise I'll be back! 💜"
        )
