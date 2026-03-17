"""
nvidia_pool.py
==============
NVIDIA NIM Pool Orchestrator — 22 keys × 1,000 credits/month = 22,000 total credits.

╔══════════════════════════════════════════════════════════════════════════════╗
║  KEY MAP — Name, Model, Purpose                                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  KEY_01  Qwen-122B General         qwen/qwen3.5-122b-a10b                  ║
║          → Massive 122B MoE model. Best for long-form content, reasoning   ║
║                                                                             ║
║  KEY_02  Mistral-Large-3 Writer A  mistralai/mistral-large-3-675b          ║
║          → 675B param writing giant. Best for Hindi stories, scripts       ║
║                                                                             ║
║  KEY_03  Gemma-3 27B General       google/gemma-3-27b-it                   ║
║          → Google's latest 27B. Good for structured tasks, SEO, summaries  ║
║                                                                             ║
║  KEY_04  Phi-4 Vision              microsoft/phi-4-multimodal-instruct     ║
║          → Reads images/screenshots. Use for image analysis, OCR, review   ║
║                                                                             ║
║  KEY_05  LLaMA-3.3 Chat A          meta/llama-3.3-70b-instruct             ║
║          → Meta's 70B chat model. Fast, sharp, great for conversation      ║
║                                                                             ║
║  KEY_06  LLaMA-3.3 Chat B          meta/llama-3.3-70b-instruct             ║
║          → Same model, second key. Doubles throughput for chat             ║
║                                                                             ║
║  KEY_07  LLaMA-4 Scout             meta/llama-4-scout-17b-16e-instruct     ║
║          → MoE 17B×16E multimodal. Fast vision+text (404 — auto-fallback)  ║
║                                                                             ║
║  KEY_08  Falcon3 Fast Chat         tiiuae/falcon3-7b-instruct              ║
║          → UAE's 7B model. Lightweight chat, casual responses              ║
║                                                                             ║
║  KEY_09  NVIDIA USD Code           nvidia/usdcode-llama-3.1-70b-instruct   ║
║          → Specialised 3D/USD scene code generation (404 — auto-fallback)  ║
║                                                                             ║
║  KEY_10  Phi-3.5 Mini General      microsoft/phi-3.5-mini-instruct         ║
║          → Small but capable. Good for classification, quick responses     ║
║                                                                             ║
║  KEY_11  Gemma-2 2B Speed          google/gemma-2-2b-it                    ║
║          → Tiny 2B model. Fastest possible response, minimal credits       ║
║                                                                             ║
║  KEY_12  ChatGLM3 6B Fast          thudm/chatglm3-6b                       ║
║          → Chinese/English bilingual 6B. Good for quick tasks              ║
║                                                                             ║
║  KEY_13  Mamba Codestral           mistralai/mamba-codestral-7b-v0.1       ║
║          → Mistral's code model. Python, JS, SQL generation & review       ║
║                                                                             ║
║  KEY_14  Phi-3 Medium 128K         microsoft/phi-3-medium-128k-instruct    ║
║          → 128K context window. Best for reading long docs, full scripts   ║
║                                                                             ║
║  KEY_15  Gemma-2 27B General       google/gemma-2-27b-it                   ║
║          → Google 27B. Strong reasoning, good fallback for writing         ║
║                                                                             ║
║  KEY_16  Phi-3 Small Fast          microsoft/phi-3-small-8k-instruct       ║
║          → Compact & fast. Good for SEO tags, metadata, short tasks        ║
║                                                                             ║
║  KEY_17  Mistral-Large-3 Writer B  mistralai/mistral-large-3-675b          ║
║          → Same giant writer, second key. Full backup for story writing    ║
║                                                                             ║
║  KEY_18  LLaMA-3.3 Chat C          meta/llama-3.3-70b-instruct             ║
║          → Third LLaMA-3.3 key. Used when A & B are rate-limited          ║
║                                                                             ║
║  KEY_19  LLaMA-3.3 Chat D          meta/llama-3.3-70b-instruct             ║
║          → Fourth key. Aisha's autonomous loop uses this for decisions     ║
║                                                                             ║
║  KEY_20  LLaMA-3.3 Chat E          meta/llama-3.3-70b-instruct             ║
║          → Fifth key. Telegram bot responses use this pool                 ║
║                                                                             ║
║  KEY_21  LLaMA-3.3 Chat F          meta/llama-3.3-70b-instruct             ║
║          → Sixth key. Reserved for content pipeline secondary tasks        ║
║                                                                             ║
║  KEY_22  LLaMA-3.3 Chat G          meta/llama-3.3-70b-instruct             ║
║          → Seventh key. Last resort chat fallback before switching provider║
╚══════════════════════════════════════════════════════════════════════════════╝

Task → Pool routing:
  "writing" → KEY_02, KEY_17 (Mistral-Large-3, best for Hindi stories/scripts)
  "chat"    → KEY_05..22 LLaMA-3.3 pool + Falcon3 (fast conversation)
  "code"    → KEY_09 USD-Code, KEY_13 Mamba-Codestral (code generation/review)
  "vision"  → KEY_04 Phi-4 Multimodal (image analysis, screenshot reading)
  "image"   → KEY_04 Phi-4 (image understanding) + general pool for prompts
  "video"   → KEY_01 Qwen-122B + KEY_14 Phi-3-128K (script/storyboard for video)
  "fast"    → KEY_11 Gemma-2-2B, KEY_12 ChatGLM3, KEY_16 Phi-3-Small
  "general" → KEY_01 Qwen-122B, KEY_03 Gemma-3-27B, KEY_10 Phi-3.5-Mini,
               KEY_14 Phi-3-128K, KEY_15 Gemma-2-27B

Total credits: 22,000/month. Aisha uses credits conservatively:
  - Fast tasks (SEO, metadata) → fast pool (cheapest)
  - Stories/scripts → writing pool (quality)
  - Chat → chat pool (balanced)
"""

import os
import time
import logging
import threading
import requests
from pathlib import Path
from typing import Optional, Dict, List

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

log = logging.getLogger("Aisha.NvidiaPool")

# ── Key pool definition ────────────────────────────────────────────────────────
# Format: (env_var_name, model, pool_category)
# Key 07 = llama-4-scout (404 in test — model may be region-locked or deprecated)
# Key 09 = usdcode-llama (404 in test — same issue; will auto-fail and skip)

_KEY_DEFINITIONS = [
    # env_var,         model,                                               pool,      label
    ("NVIDIA_KEY_01", "qwen/qwen3.5-122b-a10b",                           "general"), # Qwen-122B General
    ("NVIDIA_KEY_02", "mistralai/mistral-large-3-675b-instruct-2512",     "writing"), # Mistral-Large-3 Writer A
    ("NVIDIA_KEY_03", "google/gemma-3-27b-it",                            "general"), # Gemma-3 27B General
    ("NVIDIA_KEY_04", "microsoft/phi-4-multimodal-instruct",              "vision"),  # Phi-4 Vision (image/screenshot analysis)
    ("NVIDIA_KEY_05", "meta/llama-3.3-70b-instruct",                      "chat"),    # LLaMA-3.3 Chat A
    ("NVIDIA_KEY_06", "meta/llama-3.3-70b-instruct",                      "chat"),    # LLaMA-3.3 Chat B
    ("NVIDIA_KEY_07", "meta/llama-4-scout-17b-16e-instruct",              "vision"),  # LLaMA-4 Scout (multimodal, 404→fallback)
    ("NVIDIA_KEY_08", "tiiuae/falcon3-7b-instruct",                       "fast"),    # Falcon3 Fast Chat
    ("NVIDIA_KEY_09", "nvidia/usdcode-llama-3.1-70b-instruct",            "code"),    # NVIDIA USD Code (404→fallback)
    ("NVIDIA_KEY_10", "microsoft/phi-3.5-mini-instruct",                  "general"), # Phi-3.5 Mini General
    ("NVIDIA_KEY_11", "google/gemma-2-2b-it",                             "fast"),    # Gemma-2 2B Speed (cheapest)
    ("NVIDIA_KEY_12", "thudm/chatglm3-6b",                                "fast"),    # ChatGLM3 6B Fast
    ("NVIDIA_KEY_13", "mistralai/mamba-codestral-7b-v0.1",                "code"),    # Mamba Codestral (Python/JS/SQL)
    ("NVIDIA_KEY_14", "microsoft/phi-3-medium-128k-instruct",             "video"),   # Phi-3 Medium 128K (long video scripts)
    ("NVIDIA_KEY_15", "google/gemma-2-27b-it",                            "general"), # Gemma-2 27B General
    ("NVIDIA_KEY_16", "microsoft/phi-3-small-8k-instruct",                "fast"),    # Phi-3 Small Fast (SEO, metadata)
    ("NVIDIA_KEY_17", "mistralai/mistral-large-3-675b-instruct-2512",     "writing"), # Mistral-Large-3 Writer B
    ("NVIDIA_KEY_18", "meta/llama-3.3-70b-instruct",                      "chat"),    # LLaMA-3.3 Chat C
    ("NVIDIA_KEY_19", "meta/llama-3.3-70b-instruct",                      "chat"),    # LLaMA-3.3 Chat D (autonomous loop)
    ("NVIDIA_KEY_20", "meta/llama-3.3-70b-instruct",                      "chat"),    # LLaMA-3.3 Chat E (Telegram bot)
    ("NVIDIA_KEY_21", "meta/llama-3.3-70b-instruct",                      "chat"),    # LLaMA-3.3 Chat F (content pipeline)
    ("NVIDIA_KEY_22", "meta/llama-3.3-70b-instruct",                      "chat"),    # LLaMA-3.3 Chat G (last resort)
]

# Fallback chain: if primary pool exhausted, try these pools in order
_FALLBACK_CHAINS: Dict[str, List[str]] = {
    "writing":  ["general", "chat"],
    "chat":     ["general", "fast"],
    "code":     ["general", "chat"],
    "vision":   ["general", "chat"],       # vision → general → chat if phi-4 down
    "image":    ["vision", "general"],     # image prompts → vision model → general
    "video":    ["writing", "general"],    # video scripts → writing pool → general
    "fast":     ["general", "chat"],
    "general":  ["chat", "fast"],
}

_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
_COOLDOWN_SECONDS = 60       # Seconds to cool down a key after failure
_MAX_FAILURES_BEFORE_SKIP = 3  # Mark key as dead after 3 consecutive failures


class NvidiaPool:
    """
    NVIDIA NIM Pool Orchestrator.

    Usage:
        pool = NvidiaPool()
        text = pool.generate("chat", "You are helpful.", "Say hi in 3 words")
        stats = pool.get_stats()
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._pools: Dict[str, List[dict]] = {}
        self._pool_indices: Dict[str, int] = {}
        self._build_pools()

    def _build_pools(self):
        """Load all keys from environment and organize into pools."""
        pools: Dict[str, List[dict]] = {
            "writing": [],
            "chat":    [],
            "code":    [],
            "vision":  [],
            "image":   [],
            "video":   [],
            "fast":    [],
            "general": [],
        }

        for env_var, model, pool_name in _KEY_DEFINITIONS:
            key = os.getenv(env_var, "").strip()
            if not key or "your_" in key or not key.startswith("nvapi-"):
                log.warning(f"[NvidiaPool] {env_var} missing or invalid — skipping")
                continue
            entry = {
                "env_var":        env_var,
                "key":            key,
                "model":          model,
                "pool":           pool_name,
                "calls":          0,
                "failures":       0,
                "cooldown_until": 0.0,
            }
            pools[pool_name].append(entry)

        self._pools = pools
        self._pool_indices = {name: 0 for name in pools}

        total = sum(len(v) for v in pools.values())
        log.info(f"[NvidiaPool] Loaded {total} keys across {len(pools)} pools")
        for name, entries in pools.items():
            if entries:
                log.info(f"  {name}: {len(entries)} keys")

    def _is_key_available(self, entry: dict) -> bool:
        """Return True if this key is not in cooldown and not dead."""
        if entry["failures"] >= _MAX_FAILURES_BEFORE_SKIP:
            return False
        if time.time() < entry["cooldown_until"]:
            return False
        return True

    def _get_key(self, task_type: str) -> Optional[dict]:
        """
        Round-robin pick from the given pool.
        Returns the next available key entry, or None if pool is exhausted.
        """
        with self._lock:
            pool = self._pools.get(task_type, [])
            if not pool:
                return None

            start_idx = self._pool_indices.get(task_type, 0)
            n = len(pool)

            for i in range(n):
                idx = (start_idx + i) % n
                entry = pool[idx]
                if self._is_key_available(entry):
                    # Advance round-robin pointer
                    self._pool_indices[task_type] = (idx + 1) % n
                    return entry

            return None  # All keys in this pool are cooling down or dead

    def _mark_success(self, entry: dict):
        with self._lock:
            entry["calls"] += 1
            entry["failures"] = 0
            entry["cooldown_until"] = 0.0

    def _mark_failure(self, entry: dict, is_rate_limit: bool = False):
        with self._lock:
            entry["failures"] += 1
            if is_rate_limit:
                entry["cooldown_until"] = time.time() + _COOLDOWN_SECONDS
            else:
                backoff = min(30 * (2 ** min(entry["failures"] - 1, 3)), 300)
                entry["cooldown_until"] = time.time() + backoff
            log.warning(
                f"[NvidiaPool] {entry['env_var']} failure #{entry['failures']} "
                f"— cooldown until +{int(entry['cooldown_until'] - time.time())}s"
            )

    def _call_key(
        self,
        entry: dict,
        system_prompt: str,
        user_message: str,
        history: list,
        max_tokens: int = 16384,
        temperature: float = 0.7,
    ) -> str:
        """Make a single API call using one key entry."""
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-8:]:
            role = "assistant" if msg.get("role") in ("model", "assistant") else "user"
            messages.append({"role": role, "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        resp = requests.post(
            _NVIDIA_BASE_URL,
            headers={
                "Authorization": f"Bearer {entry['key']}",
                "Accept":        "application/json",
            },
            json={
                "model":       entry["model"],
                "messages":    messages,
                "max_tokens":  max_tokens,
                "temperature": temperature,
                "top_p":       0.95,
            },
            timeout=60,
        )

        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        elif resp.status_code == 402:
            raise Exception(f"NVIDIA credits exhausted for {entry['env_var']}")
        elif resp.status_code == 429:
            raise Exception(f"NVIDIA rate limit 429 for {entry['env_var']}")
        elif resp.status_code == 404:
            # Model not available — treat as permanent failure for this key
            entry["failures"] = _MAX_FAILURES_BEFORE_SKIP
            raise Exception(f"NVIDIA 404 model not found: {entry['model']} ({entry['env_var']})")
        else:
            raise Exception(
                f"NVIDIA {resp.status_code} from {entry['env_var']}: {resp.text[:150]}"
            )

    def generate(
        self,
        task_type: str,
        system_prompt: str,
        user_message: str,
        history: list = None,
        max_tokens: int = 16384,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate a response using the best available key for the given task type.

        Args:
            task_type:     One of: "writing", "chat", "code", "vision", "image", "video", "fast", "general"
            system_prompt: System/persona instructions
            user_message:  The user's message
            history:       Optional list of {"role": ..., "content": ...} dicts
            max_tokens:    Max tokens to generate (default 16384)
            temperature:   Sampling temperature (default 0.7)

        Returns:
            Generated text string

        Raises:
            Exception: "All NVIDIA pools exhausted" if every key fails
        """
        history = history or []

        if task_type not in self._pools:
            log.warning(f"[NvidiaPool] Unknown task_type '{task_type}', defaulting to 'general'")
            task_type = "general"

        # Build the sequence of pools to try: primary + fallback chain
        pools_to_try = [task_type] + _FALLBACK_CHAINS.get(task_type, ["general"])

        attempted_keys = set()

        for pool_name in pools_to_try:
            while True:
                entry = self._get_key(pool_name)
                if entry is None:
                    break  # No available keys in this pool — move to next pool

                key_id = entry["env_var"]
                if key_id in attempted_keys:
                    break  # Already tried all keys in this pool this call
                attempted_keys.add(key_id)

                try:
                    log.info(
                        f"[NvidiaPool] {pool_name}/{key_id} → {entry['model'][:40]}"
                    )
                    result = self._call_key(
                        entry, system_prompt, user_message, history,
                        max_tokens=max_tokens, temperature=temperature
                    )
                    self._mark_success(entry)
                    log.info(f"[NvidiaPool] {key_id} OK — {result[:60]!r}")
                    return result

                except Exception as e:
                    err = str(e)
                    is_rate = "429" in err or "rate limit" in err.lower()
                    is_credits = "402" in err or "credits" in err.lower()
                    is_404 = "404" in err

                    # 404 = model permanently gone — already marked dead inside _call_key
                    if not is_404:
                        self._mark_failure(entry, is_rate_limit=is_rate or is_credits)

                    log.warning(f"[NvidiaPool] {key_id} failed: {err[:100]}")
                    continue  # Try next key in same pool

        raise Exception(
            "All NVIDIA pools exhausted — no working keys available. "
            "Check credits or cooldown status with get_stats()."
        )

    def get_stats(self) -> Dict[str, dict]:
        """
        Returns a dict of all pools with their key stats.

        Example:
            {
                "chat": {
                    "total_keys": 8,
                    "available": 7,
                    "total_calls": 42,
                    "keys": [{"env_var": ..., "model": ..., "calls": ..., ...}]
                },
                ...
            }
        """
        with self._lock:
            stats = {}
            now = time.time()
            for pool_name, entries in self._pools.items():
                available = sum(1 for e in entries if self._is_key_available(e))
                total_calls = sum(e["calls"] for e in entries)
                key_details = []
                for e in entries:
                    key_details.append({
                        "env_var":    e["env_var"],
                        "model":      e["model"],
                        "calls":      e["calls"],
                        "failures":   e["failures"],
                        "available":  self._is_key_available(e),
                        "cooldown_remaining": max(0, int(e["cooldown_until"] - now)),
                    })
                stats[pool_name] = {
                    "total_keys":  len(entries),
                    "available":   available,
                    "total_calls": total_calls,
                    "keys":        key_details,
                }
            return stats

    def reset_failures(self, env_var: str = None):
        """
        Reset failure counters — useful after fixing a model issue.
        Pass env_var to reset a specific key, or None to reset all.
        """
        with self._lock:
            for entries in self._pools.values():
                for e in entries:
                    if env_var is None or e["env_var"] == env_var:
                        e["failures"] = 0
                        e["cooldown_until"] = 0.0
            log.info(f"[NvidiaPool] Reset failures for: {env_var or 'ALL'}")

    def __repr__(self) -> str:
        total = sum(len(v) for v in self._pools.values())
        avail = sum(
            1 for entries in self._pools.values()
            for e in entries if self._is_key_available(e)
        )
        return f"<NvidiaPool keys={total} available={avail}>"
